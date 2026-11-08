import unittest
from copy import deepcopy
from mixed_interface.normalization import exact,tag_response,tag_comparison,article_create,article_body_update,profile_update

ARTICLE={'title':'Title','description':'Description','body':'Body','tagList':['b','a','b']}
USER={'username':'user','email':'u@example.com','bio':'existing','image':None}

class NormalizationTests(unittest.TestCase):
    def test_command_order_duplicates_null_and_omission_remain_distinct(self):
        for a,b in [(['b','a'],['a','b']),(['a','a'],['a']),({}, {'bio':None}),({'bio':None},{'bio':''}),(True,1)]:
            self.assertFalse(exact(a,b))
    def test_object_key_order_is_not_json_semantics(self):
        self.assertTrue(exact({'a':1,'b':2},{'b':2,'a':1}))
    def test_expected_tag_response_is_sorted_unique(self):
        self.assertEqual(tag_response(['b','a','b']),['a','b'])
    def test_duplicate_response_is_not_hidden_by_membership(self):
        r=tag_comparison(['a'],['a','a'])
        self.assertTrue(r['membership_equal']);self.assertFalse(r['response_representation_equal'])
    def test_unsorted_response_is_not_hidden_by_membership(self):
        r=tag_comparison(['b','a'],['b','a'])
        self.assertTrue(r['membership_equal']);self.assertFalse(r['response_representation_equal'])
    def test_whitespace_and_case_are_preserved(self):
        self.assertEqual(tag_response([' A ','a']),[' A ','a'])
        self.assertEqual(profile_update(USER,{'bio':' '})['bio'],' ')
    def test_invalid_tags_do_not_become_empty(self):
        for value in (None,'tag',[1]):
            with self.assertRaises(ValueError):tag_response(value)
    def test_omitted_create_tags_default_but_null_is_invalid(self):
        self.assertEqual(article_create({k:v for k,v in ARTICLE.items() if k!='tagList'})['tagList'],[])
        with self.assertRaises(ValueError):article_create({**ARTICLE,'tagList':None})
    def test_profile_omission_preserves_but_null_clears(self):
        self.assertEqual(profile_update(USER,{})['bio'],'existing')
        self.assertIsNone(profile_update(USER,{'bio':None})['bio'])
        self.assertIsNone(profile_update(USER,{'bio':''})['bio'])
    def test_identity_changes_are_not_silently_normalized(self):
        with self.assertRaises(ValueError):profile_update(USER,{'email':'new@example.com'})
    def test_partial_article_omission_preserves_and_empty_tags_clear(self):
        self.assertEqual(article_body_update(ARTICLE,{'body':'Next'})['tagList'],['a','b'])
        self.assertEqual(article_body_update(ARTICLE,{'tagList':[]})['tagList'],[])
    def test_null_partial_article_stays_unresolved(self):
        with self.assertRaises(ValueError):article_body_update(ARTICLE,{'body':None})
    def test_invalid_create_not_predicted_as_accepted(self):
        for value in ('',None):
            with self.assertRaises(ValueError):article_create({**ARTICLE,'body':value})
    def test_inputs_are_never_mutated(self):
        saved=deepcopy(ARTICLE);article_create(ARTICLE);tag_comparison(ARTICLE['tagList'],['a','b'])
        self.assertEqual(ARTICLE,saved)
