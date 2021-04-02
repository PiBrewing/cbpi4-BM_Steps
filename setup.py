from setuptools import setup

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='cbpi4-BM_Steps',
      version='0.0.8',
      description='CraftBeerPi4 Step Plugin',
      author='Alexander Vollkopf',
      author_email='avollkopf@web.de',
      url='https://github.com/avollkopf/cbpi4-BM_Steps',
      include_package_data=True,
      license='GPLv3',
      package_data={
        # If any package contains *.txt or *.rst files, include them:
      '': ['*.txt', '*.rst', '*.yaml'],
      'cbpi4-BM_Steps': ['*','*.txt', '*.rst', '*.yaml']},
      packages=['cbpi4-BM_Steps'],
      install_requires=[
	'cbpi>=4.0.0.33',
        'numpy>=1.20',
      ],      
      long_description=long_description,
      long_description_content_type='text/markdown'
     )
