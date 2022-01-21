from setuptools import setup, find_packages

setup(
    name='app',
    version='0.1.0',
    packages=find_packages(include=['app', 'app.*']),
    install_requires=[
        'streamlit==1.1.0',
        'bokeh==2.2.3'
    ]
)