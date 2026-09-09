"""Package approved runs, one original and its outputs per ZIP folder."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package(runs, output):
    output = Path(output)
    if output.suffix.lower() != '.zip':
        raise ValueError('交付包必须为ZIP')
    entries = {}
    folders = set()
    for run in map(Path, runs):
        result = json.loads((run / 'verification.json').read_text())
        model = json.loads((run / 'input.json').read_text())
        if result.get('status') != 'passed' or result.get('errors') != []:
            raise ValueError('只能打包验收通过的运行：' + str(run))
        source = Path(model['source'])
        folder = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', source.stem).strip(' .') or '原始文件'
        base = folder
        n = 2
        while folder.casefold() in folders:
            folder = f'{base}（{n}）'
            n += 1
        folders.add(folder.casefold())

        def add(path, name, expected):
            if Path(name).name != name or name in ('.', '..'):
                raise ValueError('不合法的交付文件名')
            data = path.read_bytes()
            if digest(data) != expected:
                raise ValueError('文件自验收后发生变化：' + str(path))
            key = folder + '/' + name
            if key in entries:
                raise ValueError('交付文件重名：' + key)
            entries[key] = data

        add(source, source.name, model['source_sha256'])
        if set(result.get('deliverables', {})) != {'题目版', '答案版'}:
            raise ValueError('必须包含两版DOC')
        for variant, name in result['deliverables'].items():
            add(run / 'deliverables' / name, name, result['files'][variant]['sha256'])
        report = result.get('deletion_report')
        if model.get('removed_questions') and not report:
            raise ValueError('有删题但缺少删除记录PDF')
        if report:
            add(run / 'deliverables' / report['filename'], '浙江选考题删除记录汇总.pdf', report['sha256'])
    if not entries:
        raise ValueError('未指定已验收运行')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents silently replacing an existing delivery.
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() or set(archive.namelist()) != set(entries):
            raise ValueError('ZIP完整性检查失败')
        for name, data in entries.items():
            if archive.read(name) != data:
                raise ValueError('ZIP文件内容不一致：' + name)
    return output.resolve()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('runs', nargs='+')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(package(args.runs, args.out))
