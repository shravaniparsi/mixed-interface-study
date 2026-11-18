"""Synthetic configuration/layout tests; no Docker, startup or secret output."""
import copy
from pathlib import Path
import unittest
from provision_seatsurfing_ordinary_v1 import app_environment, verify_runtime_layout, PG_IMAGE_ID, PG, VOLUME


class ProvisionGuards(unittest.TestCase):
    def fixture(self):
        app_image = 'sha256:' + 'a' * 64
        private_key, public_key = Path('/synthetic/private.pem'), Path('/synthetic/public.pem')
        def base(image):
            return {'Image': image, 'Id': 'fixture-id', 'Config': {'Labels': {'org.mixed-interface.study': 'seatsurfing-qualification-v1'}},
                    'HostConfig': {'Privileged': False, 'PortBindings': {}, 'RestartPolicy': {'Name': 'no'}}}
        app, postgres = base(app_image), base(PG_IMAGE_ID)
        app['Config']['User'] = '65532:65532'
        app['HostConfig'].update(NetworkMode='container:' + PG, ReadonlyRootfs=True)
        app['Mounts'] = [{'Type': 'bind', 'RW': False, 'Destination': '/run/study-' + name + '.pem', 'Source': str(path)}
                         for name, path in [('private', private_key), ('public', public_key)]]
        postgres['HostConfig']['NetworkMode'] = 'none'
        postgres['Mounts'] = [{'Type': 'volume', 'Name': VOLUME, 'Destination': '/var/lib/postgresql', 'RW': True}]
        return app, postgres, app_image, private_key, public_key

    def test_isolated_fixture_layout(self):
        verify_runtime_layout(*self.fixture())

    def test_external_database_network_rejected(self):
        x = self.fixture(); x[1]['HostConfig']['NetworkMode'] = 'bridge'
        with self.assertRaises(AssertionError): verify_runtime_layout(*x)

    def test_host_port_rejected(self):
        x = self.fixture(); x[0]['HostConfig']['PortBindings'] = {'8080/tcp': [{'HostPort': '8080'}]}
        with self.assertRaises(AssertionError): verify_runtime_layout(*x)

    def test_writable_application_rejected(self):
        x = self.fixture(); x[0]['HostConfig']['ReadonlyRootfs'] = False
        with self.assertRaises(AssertionError): verify_runtime_layout(*x)

    def test_writable_key_rejected(self):
        x = self.fixture(); x[0]['Mounts'][0]['RW'] = True
        with self.assertRaises(AssertionError): verify_runtime_layout(*x)

    def test_wrong_database_image_rejected(self):
        x = self.fixture(); x[1]['Image'] = 'sha256:' + 'b' * 64
        with self.assertRaises(AssertionError): verify_runtime_layout(*x)

    def test_extra_application_mount_rejected(self):
        x = self.fixture(); x[0]['Mounts'].append(copy.deepcopy(x[0]['Mounts'][0]))
        with self.assertRaises(AssertionError): verify_runtime_layout(*x)

    def test_environment_preserves_required_bootstrap_keys(self):
        env = app_environment('a' * 48, 'b' * 48, 'c' * 32)
        self.assertEqual(len(env['CRYPT_KEY']), 32)
        self.assertEqual(env['PUBLIC_LISTEN_ADDR'], '127.0.0.1:8080')
        self.assertEqual(env['MOCK_SENDMAIL'], '1')
        self.assertEqual(env['CORS_ORIGINS'], '')
        self.assertEqual(env['RATE_LIMIT'], '250')
        self.assertEqual(env['RATE_LIMIT_PERIOD'], '1-M')
        self.assertEqual(env['PLUGINS_CONFIG'], '')
        self.assertEqual(env['INIT_ORG_DOMAIN'], 'localhost')
        with self.assertRaises(AssertionError): app_environment('bad\nvalue', 'b' * 48, 'c' * 32)
        with self.assertRaises(AssertionError): app_environment('a' * 48, 'b' * 48, 'short')


if __name__ == '__main__': unittest.main()
