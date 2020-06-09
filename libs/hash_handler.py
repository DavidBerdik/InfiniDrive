from binascii import crc32
from hashlib import sha256

# Given a byte array, calculate the CRC32 and SHA-256 hashes and return them.
def calc_hashes(bytes):
	return hex(crc32(bytes)), sha256(bytes).hexdigest()

# Given a byte array, calculate the CRC32 hash and return it.
def calc_crc32(bytes):
	return hex(crc32(bytes))

# Given a byte array, calculate the SHA-256 hash and return it.
def calc_sha256(bytes):
	return sha256(bytes).hexdigest()

# Extracts the CRC32 and SHA-256 hash values from a given InfiniDrive fragment and returns
# a pair containing them. If no CRC32 or SHA-256 value is present (older InfiniDrive versions
# did not store hashes), an empty string is returned.
def get_frag_hashes(fragment):
	crc32 = ''
	sha256 = ''

	if 'properties' in fragment:
		crc32 = fragment['properties']['crc32']
		if 'sha256' in fragment['properties']:
			sha256 = fragment['properties']['sha256']

	return crc32, sha256

# For a given fragment and associated download attempt of the fragment, determine if the remote
# fragment's hash matches the bytes that were downloaded. If they do not, return true. If they
# do, return false. If a given hash is not present, return false for backwards compatibility.
def is_download_invalid(fragment, download_bytes):
	return ('properties' in fragment and (fragment['properties']['crc32'] != calc_crc32(download_bytes) or
		('sha256' in fragment['properties'] and fragment['properties']['sha256'] != calc_sha256(download_bytes))))