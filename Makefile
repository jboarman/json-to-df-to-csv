SHELL:=/bin/bash	  # use bash shell to simplify sourcing venv in makefile

CWD=$(shell pwd)
ENV=$(CWD)/venv


default: $(ENV)

$(ENV): requirements.txt
	@# use hack to install python3.6 _AND_ pip to work around Cloud9/ubuntu issue:
	@#     http://jtannas-python-skeleton.readthedocs.io/en/latest/source/README.html#cloud9-notes
	@# other methods might include:
	@#     https://askubuntu.com/questions/412178/
	python3.6 -m venv --without-pip $(ENV) \
		&& source $(ENV)/bin/activate \
		&& curl https://bootstrap.pypa.io/get-pip.py | python \
		&& $(ENV)/bin/pip3 install -r ./requirements.txt

clean:
	rm -rf $(ENV)

run: $(ENV)
	python transform.py