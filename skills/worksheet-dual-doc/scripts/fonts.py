"""Resolve locally licensed fonts across environments; support a pinned trusted source."""
from pathlib import Path
import os,json,hashlib,urllib.request,shutil,platform
import struct


def families(path):
    """Read SFNT name records without adding a font parsing dependency."""
    try:
        data=Path(path).read_bytes()
        offsets=[0]
        if data[:4]==b'ttcf':
            count=struct.unpack_from('>I',data,8)[0]
            offsets=list(struct.unpack_from('>'+str(count)+'I',data,12))
        names=set()
        for off in offsets:
            n=struct.unpack_from('>H',data,off+4)[0]
            for i in range(n):
                tag,_,start,length=struct.unpack_from('>4sIII',data,off+12+16*i)
                if tag!=b'name':continue
                _,count,stringoff=struct.unpack_from('>HHH',data,start)
                for j in range(count):
                    platform,encoding,lang,nameid,size,pos=struct.unpack_from('>HHHHHH',data,start+6+12*j)
                    if nameid in (1,16):
                        raw=data[start+stringoff+pos:start+stringoff+pos+size]
                        names.add(raw.decode('utf-16-be' if platform in (0,3) else 'mac_roman',errors='replace'))
        return names
    except Exception:return set()

def native_families():
    """Query macOS registration, independently of LibreOffice fontconfig."""
    if platform.system() != 'Darwin':return None
    import ctypes as c
    ct=c.CDLL('/System/Library/Frameworks/CoreText.framework/CoreText')
    cf=c.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    ct.CTFontManagerCopyAvailableFontFamilyNames.restype=c.c_void_p
    cf.CFArrayGetCount.argtypes=[c.c_void_p];cf.CFArrayGetCount.restype=c.c_long
    cf.CFArrayGetValueAtIndex.argtypes=[c.c_void_p,c.c_long];cf.CFArrayGetValueAtIndex.restype=c.c_void_p
    cf.CFStringGetCString.argtypes=[c.c_void_p,c.c_char_p,c.c_long,c.c_uint32]
    cf.CFStringGetCString.restype=c.c_bool
    cf.CFRelease.argtypes=[c.c_void_p]
    arr=ct.CTFontManagerCopyAvailableFontFamilyNames();names=set()
    try:
        for i in range(cf.CFArrayGetCount(arr)):
            buf=c.create_string_buffer(1024)
            if cf.CFStringGetCString(cf.CFArrayGetValueAtIndex(arr,i),buf,1024,0x08000100):names.add(buf.value.decode())
    finally:cf.CFRelease(arr)
    return names


def font_record(path,source='local_file'):
    path=Path(path);digest=hashlib.sha256(path.read_bytes()).hexdigest()
    result={'directory':str(path.parent),'font_file':str(path),'sha256':digest,'source':source,'platform':platform.platform()}
    registered=native_families()
    result['native_registered']=None if registered is None else bool(registered & {'SimSun','宋体'})
    if registered is not None and not result['native_registered']:
        dest=Path.home()/'Library/Fonts'/('Worksheet-SimSun-'+digest[:12]+path.suffix.lower())
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()!=digest:
            raise RuntimeError('用户字体目标已存在不同文件，未覆盖：'+str(dest))
        if not dest.exists():shutil.copy2(path,dest)
        result['native_font_file']=str(dest)
        result['native_registered']=bool(native_families() & {'SimSun','宋体'})
        result['native_apps_may_need_restart']=True
        if not result['native_registered']:raise RuntimeError('已准备宋体但系统尚未识别，不能宣称本机办公软件字体可用：'+str(dest))
    return result

from functools import lru_cache

@lru_cache(maxsize=1)
def resolve_fonts():
    cache=Path(os.environ.get('WORKSHEET_FONT_CACHE',str(Path.home()/'.cache/worksheet-dual-doc/fonts')))
    cache.mkdir(parents=True,exist_ok=True)
    roots=[]
    if os.environ.get('WORKSHEET_FONT_DIR'):roots.append(Path(os.environ['WORKSHEET_FONT_DIR']))
    roots += [cache,Path('/Applications/Microsoft Word.app/Contents/Resources/DFonts'),Path('/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts'),Path('/Library/Fonts'),Path('/System/Library/Fonts'),Path.home()/'Library/Fonts',Path('/usr/share/fonts'),Path('/usr/local/share/fonts'),Path.home()/'.local/share/fonts',Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts']
    # Fast path for common font file names; inspect actual family, not only filename.
    fast=[]
    for root in roots:
        if root.exists():fast += [p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ['.ttf','.ttc','.otf'] and ('simsun' in p.name.lower() or '宋体' in p.name)]
    for p in fast:
        if families(p)&{'SimSun','宋体'}:return font_record(p)
    # Font names in WPS/cloud caches may be opaque; scan font files when fast path fails.
    roots += [Path('/System/Library/AssetsV2/com_apple_MobileAsset_Font8'),Path.home()/'Library/Containers/com.kingsoft.wpsoffice.mac/Data/Library',Path.home()/'Library/Group Containers/UBF8T346G9.Office/FontCache']
    for root in roots:
        if root.exists():
            for p in root.rglob('*'):
                if p.suffix.lower() in ['.ttf','.ttc','.otf'] and families(p)&{'SimSun','宋体'}:
                    return font_record(p)
    # Administrator/user-provided licensed HTTPS source, checksum mandatory.
    url=os.environ.get('WORKSHEET_FONT_URL');expected=os.environ.get('WORKSHEET_FONT_SHA256')
    if url and expected:
        if not url.startswith('https://'):raise RuntimeError('字体源必须使用HTTPS')
        data=urllib.request.urlopen(url,timeout=45).read(40*1024*1024)
        if hashlib.sha256(data).hexdigest()!=expected.lower():raise RuntimeError('字体下载校验失败，未使用该文件')
        temp=cache/'download.ttc';temp.write_bytes(data)
        if not families(temp)&{'SimSun','宋体'}:temp.unlink();raise RuntimeError('可信字体源未提供宋体')
        target=cache/'Simsun.ttc';temp.replace(target)
        return font_record(target,'configured_https')
    raise RuntimeError('已自动搜索系统、Office/WPS及缓存，仍无真实宋体。需提供合法宋体目录 WORKSHEET_FONT_DIR，或可信字体源 WORKSHEET_FONT_URL 和 SHA256。不会把替代字体标记为合格。')

@lru_cache(maxsize=1)
def resolve_source_font():
    """Require actual LiSu, never confuse it with the unrelated Lisu script font."""
    explicit=os.environ.get('WORKSHEET_SOURCE_FONT_FILE')
    roots=[Path.home()/'Library/Fonts',Path('/Library/Fonts'),Path('/Applications/Microsoft Word.app/Contents/Resources/DFonts'),Path.home()/'.cache/worksheet-dual-doc/fonts',Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts',Path.home()/'.local/share/fonts']
    candidates=[Path(explicit)] if explicit else []
    for root in roots:
        if root.exists():candidates.extend(p for p in root.glob('*') if p.suffix.lower() in ['.ttf','.ttc','.otf'])
    for p in candidates:
        if families(p)&{'LiSu','隶书'}:
            digest=hashlib.sha256(p.read_bytes()).hexdigest();result={'directory':str(p.parent),'font_file':str(p),'sha256':digest,'family':'隶书','pdf_family':'LiSu'}
            ns=native_families();result['native_registered']=None if ns is None else bool(ns&{'LiSu','隶书'})
            if ns is not None and not result['native_registered']:
                target=Path.home()/'Library/Fonts'/('Worksheet-LiSu-'+digest[:12]+p.suffix)
                target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise RuntimeError('隶书字体目标文件冲突，未覆盖')
                if not target.exists():shutil.copy2(p,target)
                result['native_font_file']=str(target);result['native_registered']=bool(native_families()&{'LiSu','隶书'});result['native_apps_may_need_restart']=True
            return result
    url=os.environ.get('WORKSHEET_SOURCE_FONT_URL');expected=os.environ.get('WORKSHEET_SOURCE_FONT_SHA256')
    if url and expected:
        if not url.startswith('https://'):raise RuntimeError('题源字体源必须使用HTTPS')
        data=urllib.request.urlopen(url,timeout=45).read(40*1024*1024)
        if hashlib.sha256(data).hexdigest()!=expected.lower():raise RuntimeError('题源字体下载校验失败')
        cache=Path.home()/'.cache/worksheet-dual-doc/fonts';cache.mkdir(parents=True,exist_ok=True)
        target=cache/('source-'+expected.lower()+'.ttf');target.write_bytes(data)
        if not families(target)&{'LiSu','隶书'}:target.unlink();raise RuntimeError('题源字体源未提供隶书')
        os.environ['WORKSHEET_SOURCE_FONT_FILE']=str(target)
        return resolve_source_font()
    return {'directory': '', 'family': '隶书', 'pdf_family': 'LiSu', 'native_registered': False, 'preview_fallback': True, 'note': '按用户授权保留隶书字体属性；本机预览使用替代字体，未验证真实隶书环境的字形与换行。'}
