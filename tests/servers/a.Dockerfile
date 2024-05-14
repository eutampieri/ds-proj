FROM bitnami/openldap
ENV LDAP_ADMIN_USERNAME=admin
ENV LDAP_ADMIN_PASSWORD=adminpassword
ENV LDAP_USERS=customuser
ENV LDAP_PASSWORDS=custompassword
ENV LDAP_ROOT=dc=example,dc=org
ENV LDAP_ADMIN_DN=cn=admin,dc=example,dc=org
ENV LDAP_ALLOW_ANON_BINDING=no
EXPOSE 1389