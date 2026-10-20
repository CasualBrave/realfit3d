#!/usr/bin/env python3
"""Render a fitted SMPL-X body before garment selection.

Uses Open3D's CPU RaycastingScene, interpolated vertex normals, two-light
diffuse shading, and 2x supersampling with Lanczos downsampling. This path
requires no OpenGL/EGL context or garment appearance model.

Run in the ccraft environment with SMPL-X and Open3D installed. The reference
motion's first-frame root orientation supplies the upright coordinate frame;
the renderer corrects its yaw toward the camera and sets a static arm pose.

Usage:
    python render_body_preview.py \\
      --betas-path gg_outputs_fixedsize/web_current_body/betas.pkl \\
      --output-image gg_outputs_fixedsize/web_current_body/body_preview.png
"""

import argparse
import pickle
from pathlib import Path

import numpy as np
import open3d as o3d
import open3d.core as o3c
import torch
from PIL import Image
from scipy.spatial.transform import Rotation

SCRIPT_DIR = Path(__file__).resolve().parent

# Body-only preview uses a 55-degree shoulder swing to leave an arm/torso gap.
# SMPL-X shoulder joints 15/16 occupy axis-angle slices 45:48 and 48:51.
SHOULDER_SWING_DEG = 55.0
# Same fixed permute ccraft's dataloader (datasets/ccraft.py's swap_axes)
# applies to every vertex after root_orient -- reproduced here so this
# standalone renderer's output lands in the same "Y-up, facing +Z toward the
# camera" convention as the rest of this project's renders.
SWAP_AXES_ROTATION = Rotation.from_euler("x", -90, degrees=True)


def build_body_mesh(betas_path: Path, body_model_root: Path, reference_motion: Path):
    with betas_path.open("rb") as f:
        betas_data = pickle.load(f)
    betas = np.asarray(betas_data["betas"], dtype=np.float32)
    gender = betas_data.get("gender", "neutral")

    import smplx
    model = smplx.create(str(body_model_root), model_type="smplx", gender=gender, use_pca=False)

    # --- Pose: same construction as make_display_pose_sequence, minus the
    # need for a real motion sequence (see module docstring). ---
    body_pose = torch.zeros(1, 63)
    swing = np.deg2rad(SHOULDER_SWING_DEG)
    body_pose[0, 45:48] = torch.tensor([0.0, 0.0, -swing])  # left shoulder
    body_pose[0, 48:51] = torch.tensor([0.0, 0.0, swing])   # right shoulder, mirrored

    ref = dict(np.load(reference_motion, allow_pickle=True))
    ref_root_orient = ref["root_orient"][0]
    ref_trans = ref["trans"][0] if "trans" in ref and ref["trans"].ndim >= 1 else np.zeros(3)

    # Yaw-correct so the body faces the camera -- identical math to
    # make_display_pose_sequence (see its docstring for the full derivation);
    # duplicated here rather than imported.
    root_matrix = Rotation.from_rotvec(ref_root_orient).as_matrix()
    forward_final = SWAP_AXES_ROTATION.as_matrix() @ (root_matrix @ np.array([0.0, 0.0, 1.0]))
    yaw = -np.arctan2(forward_final[0], forward_final[2])
    yaw_world = Rotation.from_euler("y", yaw).as_matrix()
    yaw_raw = SWAP_AXES_ROTATION.as_matrix().T @ yaw_world @ SWAP_AXES_ROTATION.as_matrix()
    new_root_matrix = yaw_raw @ root_matrix
    global_orient = torch.tensor(Rotation.from_matrix(new_root_matrix).as_rotvec(),
                                  dtype=torch.float32).unsqueeze(0)

    with torch.no_grad():
        output = model(betas=torch.tensor(betas).unsqueeze(0), global_orient=global_orient,
                        body_pose=body_pose, transl=torch.zeros(1, 3))
    vertices = output.vertices[0].cpu().numpy()
    faces = model.faces.astype(np.int32)

    # Apply the same post-root_orient permute as ccraft's dataloader, plus
    # re-center on the reference motion's own root translation so the body
    # sits at a plausible ground height instead of at SMPL-X's own pelvis-at-
    # origin convention.
    vertices = SWAP_AXES_ROTATION.apply(vertices + ref_trans)
    return vertices, faces


def _vertex_normals(vertices, faces):
    """Average unit face normals at each vertex, then normalize the sum."""
    tris = vertices[faces]
    face_normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    face_normals /= np.linalg.norm(face_normals, axis=1, keepdims=True) + 1e-8
    vn = np.zeros_like(vertices)
    for i in range(3):
        np.add.at(vn, faces[:, i], face_normals)
    return vn / (np.linalg.norm(vn, axis=1, keepdims=True) + 1e-8)


def render(vertices, faces, output_image: Path, width=480, height=640, supersample=2):
    """Render a full-body view with interpolated normals and a checkered floor.

    Each supersampled pixel casts one ray. Hit barycentric coordinates
    interpolate vertex normals for smooth diffuse shading.
    """
    vertex_normals = _vertex_normals(vertices, faces)

    scene = o3d.t.geometry.RaycastingScene()
    mesh_t = o3d.t.geometry.TriangleMesh(o3c.Tensor(vertices.astype(np.float32)),
                                          o3c.Tensor(faces.astype(np.uint32)))
    scene.add_triangles(mesh_t)

    render_w, render_h = width * supersample, height * supersample
    center = (vertices.min(0) + vertices.max(0)) / 2
    floor_y = vertices[:, 1].min()
    body_height = vertices[:, 1].max() - floor_y  # Y is up
    # Scale camera placement by body height, retaining headroom and floor.
    eye = np.array([center[0], floor_y + body_height * 0.95, center[2] + body_height * 1.8])
    look_at = np.array([center[0], floor_y + body_height * 0.55, center[2]])
    world_up = np.array([0.0, 1.0, 0.0])
    forward = look_at - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, world_up)
    right /= np.linalg.norm(right)
    cam_up = np.cross(right, forward)

    fov_y = np.deg2rad(34.0)
    half_h = np.tan(fov_y / 2)
    half_w = half_h * (render_w / render_h)
    xs = np.linspace(-half_w, half_w, render_w)
    ys = np.linspace(half_h, -half_h, render_h)
    grid_x, grid_y = np.meshgrid(xs, ys)
    directions = grid_x[..., None] * right + grid_y[..., None] * cam_up + forward
    directions /= np.linalg.norm(directions, axis=-1, keepdims=True)
    origins = np.broadcast_to(eye, directions.shape)
    rays = np.concatenate([origins, directions], axis=-1).astype(np.float32)

    result = scene.cast_rays(o3c.Tensor(rays))
    hit = result["t_hit"].numpy() < np.inf
    tri_idx = result["primitive_ids"].numpy()[hit]
    bary_uv = result["primitive_uvs"].numpy()[hit]  # (u, v); third weight is 1-u-v

    hit_verts = faces[tri_idx]  # (N, 3) vertex indices of each hit triangle
    w0, w1, w2 = 1.0 - bary_uv[:, 0] - bary_uv[:, 1], bary_uv[:, 0], bary_uv[:, 1]
    interp_normal = (w0[:, None] * vertex_normals[hit_verts[:, 0]]
                      + w1[:, None] * vertex_normals[hit_verts[:, 1]]
                      + w2[:, None] * vertex_normals[hit_verts[:, 2]])
    interp_normal /= np.linalg.norm(interp_normal, axis=1, keepdims=True) + 1e-8

    # Two lights (key + softer fill) plus a flat ambient term -- avoids the
    # single-hard-light look, keeps the far side of the body legibly grey
    # instead of near-black.
    key_dir = np.array([0.35, 0.55, 0.75])
    key_dir /= np.linalg.norm(key_dir)
    fill_dir = np.array([-0.5, 0.2, 0.6])
    fill_dir /= np.linalg.norm(fill_dir)
    diffuse = (np.clip(interp_normal @ key_dir, 0, 1) * 0.7
               + np.clip(interp_normal @ fill_dir, 0, 1) * 0.25)
    shade = np.clip(0.28 + diffuse, 0, 1.15)  # 0.28 ambient floor
    base_color = np.array([0.74, 0.74, 0.78])  # same flat-grey mannequin look used elsewhere

    image = np.ones((render_h, render_w, 3), dtype=np.float32)  # white background/sky
    _draw_floor(image, hit, origins, directions, eye, floor_y, body_height)
    image[hit] = np.clip(base_color[None, :] * shade[:, None], 0, 1)

    pil_image = Image.fromarray((image * 255).astype(np.uint8))
    if supersample != 1:
        pil_image = pil_image.resize((width, height), Image.LANCZOS)

    output_image.parent.mkdir(parents=True, exist_ok=True)
    pil_image.save(output_image)


def _draw_floor(image, body_hit, origins, directions, eye, floor_y, body_height,
                 cell_size=0.18):
    """Fills every pixel that missed the body but hits the y=floor_y ground
    plane with a light checker pattern (matching the checkered floor used
    throughout this project's real garment renders), fading to white/sky
    toward the horizon instead of a hard cutoff line. Mutates `image` in
    place for pixels it applies to; leaves body/sky pixels untouched."""
    t_plane = (floor_y - eye[1]) / directions[..., 1]
    floor_hit = (~body_hit) & (t_plane > 0)
    points = origins + directions * t_plane[..., None]
    checker = (np.floor(points[..., 0] / cell_size) + np.floor(points[..., 2] / cell_size)) % 2
    floor_color = np.where(checker[..., None] == 0, np.array([0.92, 0.92, 0.92]),
                            np.array([0.82, 0.82, 0.82]))
    distance = np.linalg.norm(points - eye, axis=-1)
    fade = np.clip(1.0 - (distance - body_height * 2.0) / (body_height * 3.0), 0.0, 1.0)
    floor_color = floor_color * fade[..., None] + 1.0 * (1 - fade[..., None])
    image[floor_hit] = floor_color[floor_hit]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--betas-path", type=Path, required=True)
    parser.add_argument("--output-image", type=Path, required=True)
    parser.add_argument("--body-model-root", type=Path,
        default=SCRIPT_DIR / "ccraft_data" / "aux_data" / "body_models")
    parser.add_argument("--reference-motion", type=Path,
        default=SCRIPT_DIR / "CMU" / "01" / "01_01_stageii.npz",
        help="Any real CMU/AMASS motion file -- only its frame-0 root_orient/trans are used, "
             "purely as a known-good geometric anchor (see module docstring).")
    args = parser.parse_args()

    vertices, faces = build_body_mesh(args.betas_path, args.body_model_root, args.reference_motion)
    render(vertices, faces, args.output_image)
    print(f"Wrote body preview: {args.output_image}")


if __name__ == "__main__":
    main()
