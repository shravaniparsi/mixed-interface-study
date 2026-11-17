#!/usr/bin/env python3
"""Record the bounded web-tool publisher observation, not a raw-HTML archive."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PRIVATE=Path('/private/tmp/development-book-lead-v1-web-result.json')
OUT=ROOT/'manifests/development-book-lead-v1.json'
def build():
    raw=PRIVATE.read_bytes();returned=json.loads(raw);assert isinstance(returned,str)
    for token in ['https://www.infoq.com/minibooks/jhipster-mini-book-7/','The JHipster Mini-Book 7.0','Mar 07, 2023','JHipster 7','Download PDF','Download ePub']:
        assert token in returned
    return dict(kind='bounded_publisher_page_observation',freeze='047e220',
        requested_url='https://www.infoq.com/minibooks/jhipster-mini-book/',
        returned_url='https://www.infoq.com/minibooks/jhipster-mini-book-7/',
        tool='web.open',opens=1,searches=0,linked_pages_opened=0,
        private_tool_result_sha256=hashlib.sha256(raw).hexdigest(),
        evidence_type='web_tool_returned_text_not_raw_publisher_html',
        title='The JHipster Mini-Book 7.0',publisher_displayed_date='2023-03-07',
        author='Matt Raible',stated_framework_major='JHipster 7',
        landing_page_access='public_text_returned',downloads_advertised=['PDF','ePub'],
        download_access_tested=False,book_text_read=False,
        exact_application_revision_compatibility='unverified',
        operation_specific_requirements_on_landing_page='not_established',
        independent_evaluation_cases=0,resolved_selected_operation_labels=0,
        next_lead='Public book blog linked on landing page; not opened in this stage.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if a.verify:assert OUT.read_text()==text;print('Recorded publisher metadata matches retained web-tool observation')
    else:OUT.write_text(text)
