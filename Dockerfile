FROM ubuntu:latest
LABEL authors="esteb"

ENTRYPOINT ["top", "-b"]