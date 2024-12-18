
from setuptools import setup

setup(name='jslog4kube',
      version='1.0.1',
      description='relatively hassle-free JSON logging for Kubernetes pods',
      url='http://gitlab.com/stephen6/jslog4kube',
      author='Stephen D. Spencer',
      author_email='stephen@revsys.com',
      license='MIT',
      packages=['jslog4kube',
                'jslog4kube.kube',
                'jslog4kube.gunicorn'],
      install_requires=[
          'python-json-logger==2.0.7',
      ],
      zip_safe=False)
