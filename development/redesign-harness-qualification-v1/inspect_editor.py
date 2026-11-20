"""Read inert archived HTML; do not load a browser or execute application code."""
import argparse,hashlib,json,pathlib,zipfile
from html.parser import HTMLParser
class Node:
 def __init__(self,tag='',attrs=(),parent=None):self.tag=tag;self.attrs=dict(attrs);self.parent=parent;self.children=[];self.text=''
 def walk(self):
  yield self
  for c in self.children:yield from c.walk()
 def content(self):return self.text+''.join(c.content() for c in self.children)
class Tree(HTMLParser):
 def __init__(self):super().__init__();self.root=Node();self.current=self.root
 def handle_starttag(self,t,a):
  n=Node(t,a,self.current);self.current.children.append(n)
  if t not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']:self.current=n
 def handle_startendtag(self,t,a):self.handle_starttag(t,a);self.handle_endtag(t)
 def handle_endtag(self,t):
  n=self.current
  while n.parent and n.tag!=t:n=n.parent
  if n.parent:self.current=n.parent
 def handle_data(self,d):self.current.text+=d

def inspect(html,name):
 p=Tree();p.feed(html)
 rows=[n for n in p.root.walk() if n.tag=='tr' and any(x.tag=='a' and x.content().strip()==name for x in n.walk())]
 assert len(rows)==1,'expected exactly one matching native table row'
 buttons=[n for n in rows[0].walk() if n.tag=='button' and any(x.tag=='svg' and 'tabler-icon-pencil' in x.attrs.get('class','').split() for x in n.walk())]
 assert len(buttons)==1,'expected exactly one edit button within matched row'
 assert 'disabled' not in buttons[0].attrs,'native edit button disabled'
 return {'matching_rows':len(rows),'matching_edit_buttons':len(buttons),'disabled':False}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('archive',type=pathlib.Path);a=ap.parse_args()
 raw=a.archive.read_bytes();assert hashlib.sha256(raw).hexdigest()=='f6736d8ca7c334574fbe0269e2c24d6edd2897db9e426152287e908d4fa519d7'
 with zipfile.ZipFile(a.archive) as z:html=z.read('failure.html')
 result=inspect(html.decode(),'research-api')
 result.update(status='inert_dom_selector_candidate_verified',html_sha256=hashlib.sha256(html).hexdigest(),source_run=44731373501,selector="page.getByRole('row').filter({has:page.getByRole('link',{name:'research-api',exact:true})}).getByRole('button').filter({has:page.locator('svg.tabler-icon-pencil')})",application_executed=False,native_edit_qualified=False,scientific_cases=0)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
