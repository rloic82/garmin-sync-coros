
import base64

import json


def decode(credient):
  salt = "9y78gpoERW4lBNYL"  # Salt value

  # Step 1: Remove the salt
  encode_credient = credient.replace(salt, '')

  # Step 2: Base64 decode
  credients = base64.b64decode(encode_credient).decode('utf-8')  # Decode to utf-8 string

  return json.loads(credients)
