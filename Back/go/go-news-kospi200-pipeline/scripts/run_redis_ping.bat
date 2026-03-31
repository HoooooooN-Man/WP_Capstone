@echo off
cd /d D:\Workspace\WP_Capstone\Back\go\go-news-kospi200-pipeline
set APP_ENV_FILE=configs\.env
go run .\cmd\redis_ping
