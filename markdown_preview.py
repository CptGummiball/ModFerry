"""Server-rendered Markdown preview; sanitize all generated HTML before browser insertion."""
import bleach
import markdown
from messages import UserError

TAGS=set(bleach.sanitizer.ALLOWED_TAGS)|{'p','h1','h2','h3','h4','h5','h6','br','hr','pre','code','img','table','thead','tbody','tr','th','td','del','input','div','span','sup','sub','details','summary'}
ATTRS={**bleach.sanitizer.ALLOWED_ATTRIBUTES,
       'a':['href','title'], 'img':['src','alt','title','width','height'],
       'code':['class'], 'th':['align'], 'td':['align'],
       'input':['type','checked','disabled'], 'div':['class'],'span':['class']}

def render(text):
    if not isinstance(text,str) or len(text)>200000:
        raise UserError('err.markdown')
    raw=markdown.markdown(text, extensions=['extra','sane_lists','nl2br','smarty'], output_format='html5')
    return bleach.clean(raw, tags=TAGS, attributes=ATTRS, protocols=['http','https','mailto'],strip=True)
