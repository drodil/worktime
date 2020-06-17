from setuptools import setup, find_packages

setup(name='worktime',
      version='0.1.0',
      packages=find_packages(),
      install_requires=[
        'python-dateutil'
      ],
      entry_points={
          'console_scripts': [
              'worktime = worktime.__main__:main'
          ]
      },
)
