import hashlib
import hmac
import unittest

from françoise.mail import (
    parse_to_header,
    parse_conversation_id_from_headers,
    verify_signature,
)


def sign(api_key: str, timestamp: str, token: str) -> str:
    return hmac.new(
        key=api_key.encode(),
        msg=(timestamp + token).encode(),
        digestmod=hashlib.sha256).hexdigest()


class TestMail(unittest.TestCase):
    def test_parse_to_header(self):
        headers = '[["To","\"Boku.2\" <foo@bar.com>"]]'
        to = parse_to_header(headers)
        self.assertEqual(to, '"\"Boku.2\" <foo@bar.com>"')

    def test_parse_conversation_id_from_headers(self):
        headers = '[["To","\"Boku.2\" <foo@bar.com>"]]'
        conversation_id = parse_conversation_id_from_headers(headers)
        self.assertEqual(conversation_id, 2)

    def test_verify_signature_valid(self):
        signature = sign('key', '12345', 'abc')
        self.assertTrue(verify_signature('key', '12345', 'abc', signature))

    def test_verify_signature_forged(self):
        self.assertFalse(verify_signature('key', '12345', 'abc', 'deadbeef'))

    def test_verify_signature_missing_fields(self):
        self.assertFalse(verify_signature('key', '', '', ''))


if __name__ == '__main__':
    unittest.main()
