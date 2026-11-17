"""Development syntax safeguards, not frontend runtime observations."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from mixed_interface.angular_template_inventory import inventory
class TemplateTests(unittest.TestCase):
    def parse(self,s):return inventory(s,'synthetic')
    def test_message_not_validator(self):
        x=self.parse('<small *ngIf="email.errors.required">Email required</small><input type="email" name="email">')
        self.assertEqual(x['controls'][0]['constraints'],[]);self.assertEqual(x['complete_api_rules'],0)
    def test_literal_template_binding(self):
        x=self.parse('<form #f="ngForm"><input [(ngModel)]="user.name" required minlength=2 maxlength="40" pattern="[A-Z]+"></form>')
        r=x['controls'][0];self.assertEqual(len(r['constraints']),4);self.assertEqual(r['form_indices'],[0]);self.assertEqual(r['bindings'][0]['value'],'user.name')
    def test_dynamic_and_interpolated_remain_unresolved(self):
        r=self.parse('<input [required]="needed" minlength="{{minimum}}" [attr.maxlength]="limit">')['controls'][0]
        self.assertEqual(len(r['dynamic_constraints']),2);self.assertEqual(r['constraints'][0]['status'],'unresolved')
    def test_false_string_not_silently_true(self):
        r=self.parse('<input required="false">')['controls'][0];self.assertEqual(r['constraints'][0]['status'],'unresolved')
    def test_parent_and_own_context(self):
        r=self.parse('<div *ngIf="loaded"><input *ngIf="allowed" required></div>')['controls'][0]
        self.assertEqual(len(r['context']),2)
    def test_activity_and_submission_retained(self):
        x=self.parse('<form (ngSubmit)="save()"><input [disabled]="locked" readonly><button [disabled]="form.invalid">Save</button></form>')
        self.assertEqual(len(x['controls'][0]['activity_attributes']),2);self.assertEqual(len(x['submission_elements']),2)
    def test_custom_control_and_duplicate(self):
        r=self.parse('<custom-picker formControlName="thing" required required>')['controls'][0]
        self.assertEqual(len(r['unresolved']),2)
    def test_comments_do_not_add_constraints(self):
        self.assertEqual(self.parse('<!-- <input required> -->')['controls'],[])
    def test_block_syntax_not_claimed_parsed(self):
        self.assertTrue(self.parse('@if (ok) {<input required>}')['unresolved'])
    def test_input_type_not_validator(self):
        r=self.parse('<input type="number" min="3">')['controls'][0];self.assertEqual(r['constraints'][0]['status'],'unresolved')
if __name__=='__main__':unittest.main()
