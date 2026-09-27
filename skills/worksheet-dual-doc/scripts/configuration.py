"""Resolve confirmed repository defaults and explicit per-run overrides."""
import json
from pathlib import Path
from common import ROOT


def resolve(overrides=None, root=ROOT):
    base=Path(root)/'assets/defaults.json'
    cfg=json.loads(base.read_text());origins={k:'repository' for k in cfg}
    overrides=overrides or {}
    if not isinstance(overrides,dict) or set(overrides)-set(cfg):
        raise ValueError('未知配置项或配置格式错误')
    cfg.update(overrides);origins.update({k:'explicit' for k in overrides})
    return cfg, {'field_sources':origins, 'explicit_overrides':overrides}


def require_names(cfg):
    for key in ('compiler','proofreader'):
        if not isinstance(cfg[key],str) or not cfg[key].strip():
            raise ValueError('尚未配置编制人/校对人；请保存仓库默认值或明确指定，不能使用示例姓名交付')


def check_resolution(info):
    record=info.get('config_resolution')
    if record is None:return []  # Legacy runs have no provenance; reported separately.
    cfg, expected=resolve(record.get('explicit_overrides',{}))
    if cfg!=info['config'] or record!=expected:
        return ['运行配置与仓库默认值/明确覆盖不一致，需重新生成']
    try:require_names(cfg)
    except ValueError as e:return [str(e)]
    return []
