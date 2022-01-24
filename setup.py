from setuptools import setup, find_packages

setup(
    name='stream',
    version='0.1.0',
    packages=find_packages(include=['stream', 'stream.*']),
    install_requires=[
        'streamlit==1.1.0',
        'bokeh==2.2.3'
    ]
)
