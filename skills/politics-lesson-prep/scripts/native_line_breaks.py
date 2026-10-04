"""Measured native-PPT wrapping at legal Chinese and numeral boundaries.

Same boundary policy as lesson-image-ppt/scripts/line_breaks.mjs. Measurement is
injected by the adapter using the actual font, weight and size. Never edit words.
"""
import math
import re

CLOSING=set('，。；：！？、）】》〉〕］｝”’％%,.!?;:)]}…')
OPENING=set('（【《〈〔［｛“‘([{')
TOKENS=re.compile(r'[A-Za-z]+(?:[0-9]+)?|[0-9]+(?:[.,．][0-9]+)*(?:[—–~～-][0-9]+(?:\.[0-9]+)*)?(?:[%％]|分钟|分|年|月|日|个|项|点|次|倍|万|亿|元|人|页|课|框|目|条)?[、.]?|[①-⑳]|——')


def line_errors(lines):
    errors=[]
    for i,line in enumerate(lines,1):
        stripped=line.strip()
        if not stripped:continue
        if stripped[0] in CLOSING:errors.append(f'line {i}: closing punctuation at start')
        if stripped[-1] in OPENING:errors.append(f'line {i}: opening punctuation at end')
        if re.fullmatch(r'(?:\d+[.、．]|[①-⑳])',stripped):
            errors.append(f'line {i}: isolated enumeration')
    return errors


def wrap_native_text(text, width, measure, safety=0):
    """Return lines for BOTH height measurement and actual OOXML writing.

    width excludes text-box insets; safety is an additional renderer allowance.
    measure(str) must use the actual styled font (bold != regular). If native
    soft-wrap remains enabled, reserve a measured safety allowance and verify
    rendered rows: XML-only checks cannot detect viewer-induced second wrapping.
    """
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (width,safety)) or safety<0 or width<=safety:
        raise ValueError('Invalid text width')
    limit=width-safety;result=[]
    for para in str(text).split('\n'):
        if not para:result.append('');continue
        if line_errors([para]):
            raise ValueError('Source paragraph starts/ends with isolated punctuation; repair layout line breaks without deleting punctuation')
        forbidden=set()
        for token in TOKENS.finditer(para):
            forbidden.update(range(token.start()+1,token.end()))
            if re.search(r'[、.]$|^[①-⑳]$',token.group()):
                # Keep the marker, intervening spaces and first content glyph together.
                end=token.end()
                while end<len(para) and para[end].isspace():end+=1
                forbidden.update(range(token.end(),min(end+1,len(para))))
        def legal(end):
            if end==len(para):return True
            return (end not in forbidden and para[end] not in CLOSING and
                    para[end-1] not in OPENING and not para[end].isspace())
        start=0
        while start<len(para):
            best=None
            for end in range(start+1,len(para)+1):
                value=measure(para[start:end])
                if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                    raise ValueError('Invalid font measurement')
                if value>limit:break
                if legal(end):best=end
            if best is None:
                raise ValueError('Unbreakable text exceeds column width; widen or use bounded font adjustment')
            result.append(para[start:best]);start=best
    errors=line_errors(result)
    if errors:raise ValueError('; '.join(errors))
    return result
