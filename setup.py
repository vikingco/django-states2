from setuptools import setup, find_packages
import states2


setup(
    name="django-states2",
    version=states2.__version__,
    url='https://github.com/citylive/django-states2',
    license='BSD',
    description="State machine for django models",
    long_description=open('README.rst', 'r').read(),
    author='Jonathan Slenders, City Live nv',
    packages=find_packages('.'),
    #package_dir={'': 'templates/*'},
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Framework :: Django',
    ],
)
