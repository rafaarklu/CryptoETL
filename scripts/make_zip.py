import shutil
import os
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
shutil.make_archive(os.path.join(root, 'DELIVERABLE'), 'zip', root)
print('Created', os.path.join(root, 'DELIVERABLE.zip'))
