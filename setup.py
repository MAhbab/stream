from setuptools import setup, find_packages

setup(
    name='stream',
    version='0.1.0',
    packages=find_packages(include=['stream', 'stream.*']),
    install_requires=[
        'streamlit>=1.7.0',
        'bokeh>=2.4.1',
        'treelib>=1.6.1',
        'bt>=0.2.9'
    ]
)
