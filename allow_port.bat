@echo off
echo 正在尝试通过防火墙放行 Streamlit 端口 (8501)...
netsh advfirewall firewall add rule name="Streamlit Web" dir=in action=allow protocol=TCP localport=8501
echo.
echo ✅ 端口 8501 已放行！请重新尝试用手机访问。
pause