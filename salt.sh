source ~/salt_venv/bin/activate
echo BASH: Running scripts for Sanford, Orlando \(Old Salt App\) and Orlando \(New Salt App\) ...
python salt/run_scheduled_automation.py -d $1
