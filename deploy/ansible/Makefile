INVENTORY ?= inventory.ini
PLAYBOOK ?= playbook.yml
VAULT_PASSWORD_FILE ?= vault_pswd
VAULT_EDITOR ?= nano
ANSIBLE_ENV = ANSIBLE_LOCAL_TEMP=/tmp/ansible-local ANSIBLE_REMOTE_TEMP=/tmp/ansible-remote
ANSIBLE_PLAYBOOK = $(ANSIBLE_ENV) ansible-playbook -i $(INVENTORY) $(PLAYBOOK) --vault-password-file $(VAULT_PASSWORD_FILE)
ANSIBLE = $(ANSIBLE_ENV) ansible -i $(INVENTORY)

.PHONY: help roles ping syntax prepare security firewall backup deploy nginx all ps logs migrate vault-edit

roles:
	ansible-galaxy collection install -r requirements.yml

ping:
	$(ANSIBLE) webservers -m ping

prepare:
	$(ANSIBLE_PLAYBOOK) --tags prepare

security:
	$(ANSIBLE_PLAYBOOK) --tags security

firewall:
	$(ANSIBLE_PLAYBOOK) --tags firewall

backup:
	$(ANSIBLE_PLAYBOOK) --tags backup

deploy:
	$(ANSIBLE_PLAYBOOK) --tags deploy

nginx:
	$(ANSIBLE_PLAYBOOK) --tags nginx

all:
	$(ANSIBLE_PLAYBOOK)

ps:
	$(ANSIBLE) webservers -b -m command -a "docker compose -f /opt/hotels-webapp/docker-compose.production.yml ps"

logs:
	$(ANSIBLE) webservers -b -m command -a "docker compose -f /opt/hotels-webapp/docker-compose.production.yml logs --tail=100"

migrate:
	$(ANSIBLE) webservers -b -m command -a "docker compose -f /opt/hotels-webapp/docker-compose.production.yml exec -T backend uv run python manage.py migrate --noinput"

vault-edit:
	EDITOR=$(VAULT_EDITOR) $(ANSIBLE_ENV) ansible-vault edit group_vars/vault.yml --vault-password-file $(VAULT_PASSWORD_FILE)
