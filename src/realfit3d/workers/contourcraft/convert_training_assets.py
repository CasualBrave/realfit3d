"""CLI bridge to the pinned upstream GauGarConverter (no algorithm changes)."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('gg-data-root', 'gg-output-root', 'body-model-root', 'checkpoint', 'garment-dicts'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--sequence', required=True)
    parser.add_argument('--gender', choices=['male', 'female'], required=True)
    parser.add_argument('--frame', type=int, required=True)
    args = parser.parse_args()
    from utils.defaults import DEFAULTS
    from utils.gaugar import GauGarConverter
    config = Path(DEFAULTS.project_dir) / 'configs/finetune' / (args.subject + '.yaml')
    stage4 = args.gg_output_root / args.subject / 'stage4'
    if config.exists() or stage4.exists():
        raise FileExistsError('Refusing to overwrite existing Stage4/config; review and archive it first')
    converter = GauGarConverter(args.gg_data_root, args.gg_output_root, args.body_model_root,
                                args.garment_dicts, args.checkpoint)
    converter.convert_subject(args.subject, args.gender, args.sequence, args.frame)


if __name__ == '__main__':
    main()
