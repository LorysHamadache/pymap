from setuptools import setup

setup(
    name='pymap',
    version='0.1',
    py_modules=['generate_mapping'],
    entry_points={
        'console_scripts': [
            'pymap = generate_mapping:main',
        ],
    },
)
