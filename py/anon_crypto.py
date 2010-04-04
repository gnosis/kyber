#
# CRYPTO PRIMITIVES FOR ANON PROTOCOL
#

import M2Crypto.EVP, M2Crypto.RSA, M2Crypto.Rand
from utils import Utilities
import tempfile, struct, cPickle

class AnonCrypto: 
	# A very unsecure initialization vector
	AES_IV = 'al*73lf9)982'
	KEYFILE_PASSWORD = '12f*d4&^#)!-1728410df' 

	
	@ staticmethod
	def key_password(input):
		return AnonCrypto.KEYFILE_PASSWORD

#
# RSA Encryption
#
# We do this the standard way: 
# 1) Encrypt the msg with a random AES key
# 2) Encrypt the AES key with the RSA key
# 3) The ciphertext is the (encrypted-AES-key, AES-ciphertext) tuple
#

	@staticmethod
	def encrypt_with_rsa(pubkey, msg):
		session_key = M2Crypto.Rand.rand_bytes(32)
		
		# AES must be padded to make 16-byte blocks
		# Since we prepend msg with # of padding bits
		# we actually need one less padding bit
		n_padding = ((16 - (len(msg) % 16)) - 1) % 16
		padding = '\0' * n_padding

		pad_struct = struct.pack('!B', n_padding)

		encrypt = M2Crypto.EVP.Cipher('aes_256_cbc', 
				session_key, AnonCrypto.AES_IV, M2Crypto.encrypt)

		# Output is tuple (E_rsa(session_key), E_aes(session_key, msg))
		return cPickle.dumps((
					pubkey.public_encrypt(session_key,
						M2Crypto.RSA.pkcs1_oaep_padding),
					encrypt.update(pad_struct + msg + padding)))

	@staticmethod
	def decrypt_with_rsa(privkey, ciphertuple):
		# Input is tuple (E_rsa(session_key), E_aes(session_key, msg))
		session_cipher, ciphertext = cPickle.loads(ciphertuple) 
		
		# Get session key using RSA decryption
		session_key = privkey.private_decrypt(session_cipher, 
				M2Crypto.RSA.pkcs1_oaep_padding)
		
		# Use session key to recover string
		dummy_block =  ' ' * 8
		decrypt = M2Crypto.EVP.Cipher('aes_256_cbc', 
				session_key, AnonCrypto.AES_IV, M2Crypto.decrypt)

		outstr = decrypt.update(ciphertext) + decrypt.update(dummy_block)
		pad_data = outstr[0]
		outstr = outstr[1:]

		# Get num of bytes added at end
		n_padding = struct.unpack('!B', pad_data)
		
		# Second element of tuple is always empty for some reason
		n_padding = n_padding[0]
		outstr = outstr[:(len(outstr) - n_padding)]

		return outstr

	@staticmethod
	def random_key(key_len):
		return M2Crypto.RSA.gen_key(key_len, 65537)

#
# HASH Function (We use SHA1)
#

	@staticmethod
	def hash(msg):
		h = M2Crypto.EVP.MessageDigest('sha1')
		h.update(msg)
		return h.final()

	# Get a hash value for a list
	@staticmethod
	def hash_list(lst):
		return AnonCrypto.hash(cPickle.dumps(lst))

#
# I/O Utility Functions
#

	@staticmethod
	def priv_key_to_str(privkey):
		return privkey.as_pem(callback = AnonCrypto.key_password)

	@staticmethod
	def priv_key_from_str(key_str):
		(handle, filename) = tempfile.mkstemp()
		Utilities.write_str_to_file(filename, key_str)
		key = M2Crypto.RSA.load_key(filename, callback = AnonCrypto.key_password)
		if not key.check_key(): raise RuntimeError, 'Bad key decode'
		return key

	@staticmethod
	def pub_key_to_str(pubkey):
		(handle, filename) = tempfile.mkstemp()
		pubkey.save_key(filename)
		return Utilities.read_file_to_str(filename)

	@staticmethod
	def pub_key_from_str(key_str):
		(handle, filename) = tempfile.mkstemp()
		Utilities.write_str_to_file(filename, key_str)
		return M2Crypto.RSA.load_pub_key(filename)
	

