import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

with open('requirements.txt', 'r') as f:
    requirements = f.read().splitlines()
    requirements = [l for l in requirements if not l.startswith('#')]

setuptools.setup(
    name='banc',
    version='0.4.0',
    author='Jasper Phelps',
    author_email='jasper.s.phelps@gmail.com',
    description="Tools for the GridTape-TEM dataset of an adult female"
                " fly's Brain And Nerve Cord",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/jasper-tms/the-BANC-fly-connectome',
    packages=['banc', 'banc.transforms'],
    package_data={'banc.transforms': ['transform_parameters/*.txt']},
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=requirements
)
