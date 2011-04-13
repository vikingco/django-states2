from setuptools import setup, find_packages


setup(
    name="django-states2",
    version="0.1",
    url='https://github.com/citylive/django-states2',
    license='BSD',
    description="State machine for django models",
    long_description=open('README.rst', 'r').read(),
    author='Jonathan Slenders, City Live nv',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Framework :: Django',
    ],
)
