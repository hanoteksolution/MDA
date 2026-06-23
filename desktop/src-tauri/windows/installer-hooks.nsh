; Stop running MDA ERP processes before upgrade/reinstall so sidecar files are not locked.
!macro NSIS_HOOK_PREINSTALL
  nsExec::ExecToLog 'taskkill /F /IM mda-api.exe /T'
  nsExec::ExecToLog 'taskkill /F /IM mda-erp-desktop.exe /T'
  Sleep 1000
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  nsExec::ExecToLog 'taskkill /F /IM mda-api.exe /T'
  nsExec::ExecToLog 'taskkill /F /IM mda-erp-desktop.exe /T'
  Sleep 1000
!macroend
