from datetime import datetime

# Check if Google's new quota rules are being enforced. Return true if they are.
# More information: https://blog.google/products/photos/storage-policy-update/
def is_quota_enforced():
	return datetime.now() >= datetime(2021, 6, 1)