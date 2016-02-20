import os
import contextlib
import unittest
import warnings
import flask
import sys
sys.path.append(os.getcwd())
import flask_dotenv as dotenv


@contextlib.contextmanager
def capture():
    import sys
    from io import StringIO
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = [StringIO(), StringIO()]
        sys.stdout, sys.stderr = out
        yield out
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()


class DotEnvTestCase(unittest.TestCase):
    def setUp(self):
        self.app = flask.Flask(__name__)
        self.env = dotenv.DotEnv()

    def tearDown(self):
        config_keys = [
            'FOO',
            'SECRET_KEY',
            'DEVELOPMENT_DATABASE_URL',
            'TEST_DATABASE_URL',
            'DATABASE_URL',
            'BAR',
            'FEATURES',
            'NUMERIC'
        ]
        for key in config_keys:
            if key in self.app.config:
                del self.app.config[key]

    def test_warning_if_env_file_is_missing(self):
        with warnings.catch_warnings(record=True) as w:
            self.env.init_app(self.app, "/does/not/exist/.env")
            self.assertEqual(
                "can't read /does/not/exist/.env - it doesn't exist",
                str(w[0].message)
            )
        self.assertFalse('FOO' in self.app.config)

    def test_read_default_env_file(self):
        self.env.init_app(self.app)
        self.assertTrue('FOO' in self.app.config)

    def test_read_specified_env_file(self):
        root_dir = os.path.dirname(os.path.abspath(__file__))
        self.env.init_app(self.app, os.path.join(root_dir, '.env.min'))
        self.assertTrue('BAR' in self.app.config)

    def test_loaded_value_dose_not_contain_double_quote(self):
        self.env.init_app(self.app)
        self.assertEqual(
            'postgresql://postgres:postgres@localhost/development',
            self.app.config['DEVELOPMENT_DATABASE_URL'])

    def test_loaded_value_dose_not_contain_single_quote(self):
        self.env.init_app(self.app)
        self.assertEqual(
            'postgresql://postgres:postgres@localhost/test',
            self.app.config['TEST_DATABASE_URL'])

    def test_loaded_value_can_contain_equal_signs(self):
        self.env.init_app(self.app)
        self.assertEqual(
            'postgresql://postgres:postgres@localhost/production?sslmode=require',
            self.app.config['DATABASE_URL'])

    def test_loaded_value_is_evaluated_as_abstract_syntax_grammar_object(self):
        self.env.init_app(self.app)
        self.assertEqual({'DotEnv': True}, self.app.config['FEATURES'])

    def test_loaded_value_is_evaluated_as_abstract_syntax_grammar_numeric(self):
        self.env.init_app(self.app)
        self.assertEqual(15, self.app.config['NUMERIC'])

    def test_overwrite_an_existing_config_var(self):
        # flask has secret_key in default
        self.assertEqual(None, self.app.config['SECRET_KEY'])
        self.env.init_app(self.app)
        self.assertEqual(':)', self.app.config['SECRET_KEY'])

    def test_alias_sets_it_as_same_value(self):
        self.env.init_app(self.app)
        self.env.alias(maps={
            'TEST_DATABASE_URL': 'SQLALCHEMY_DATABASE_URL'
        })
        self.assertEqual(
            'postgresql://postgres:postgres@localhost/test',
            self.app.config['SQLALCHEMY_DATABASE_URL']
        )

    def test_init_app_assigns_app(self):
        self.env.init_app(self.app)
        self.assertEqual(self.app, self.env.app)

    def test_init_app_assigns_default_verbose_mode(self):
        self.env.init_app(self.app)
        self.assertFalse(self.env.verbose_mode)

    def test_import_vars_raises_in_env_file_does_not_exist(self):
        with self.assertRaises(FileNotFoundError) as e:
            self.env._DotEnv__import_vars('/does/not/exist/.env')
        self.assertEqual(e.exception.strerror, 'No such file or directory')

    def test_import_vars_will_output_logs_in_vobose_mode(self):
        with capture() as out:
            self.env.app = self.app
            self.env.verbose_mode = True
            root_dir = os.path.dirname(os.path.abspath(__file__))
            self.env._DotEnv__import_vars(os.path.join(root_dir, '.env.min'))
        # flask has secret_key in default
        self.assertIn(
            " * BAR: Couldn't evaluate syntax of value on .env line:\n"
            "     BAR=true\n"
            "   Importing as string value.\n"
            " * Setting an entirely new config var: BAR\n"
            " * SECRET_KEY: value ':)' of type <class 'str'> cast to <class 'str'>\n"
            " * Overwriting an existing config var: SECRET_KEY\n",
            out
        )

    def test_alias_will_output_log_in_vobose_mode(self):
        with capture() as out:
            self.env.init_app(self.app)
            self.env.verbose_mode = True
            self.env.alias(maps={
                'TEST_DATABASE_URL': 'SQLALCHEMY_DATABASE_URL'
            })
        self.assertIn(
            ' * Mapping a specified var as a alias:'
            ' SQLALCHEMY_DATABASE_URL => TEST_DATABASE_URL\n',
            out
        )

if __name__ == '__main__':
    unittest.main()
