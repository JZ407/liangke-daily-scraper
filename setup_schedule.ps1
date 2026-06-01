$action = New-ScheduledTaskAction -Execute 'C:\Python314\python.exe' -Argument '-X utf8 D:\Claude_code\liangke_daily\core\scrape_daily.py'
$trigger = New-ScheduledTaskTrigger -Daily -At '13:00'
Register-ScheduledTask -TaskName 'QTC_DailyScrape' -Action $action -Trigger $trigger -Force
Write-Host "Task 'QTC_DailyScrape' created successfully"
