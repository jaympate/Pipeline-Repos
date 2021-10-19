
// start/stop IIS application pool at remote server using powershell script 
def iisAppPoolExecute_PS(action,application_pool_name,server_name,server_credentials){
	echo " Performing $action App Pool ${application_pool_name} - @ ${server_name} " + currentTime()
	def iisAppPool_script = libraryResource 'iis-app-pool-script.ps1'
  	writeFile file: 'iis-app-pool-script.ps1', text: iisAppPool_script
	iisAppPool_script_path = ".\\iis-app-pool-script.ps1"
    withCredentials([usernamePassword(credentialsId: "$server_credentials", passwordVariable: 'server_password', usernameVariable: 'server_username')]){
		echo " triggering iis app pool script : ${iisAppPool_script_path}  "
		iisAppPool_script_parameter = " '${action}' '${application_pool_name}' '${server_name}' '${server_username}' '${server_password}'" 
        def output=powershell ( returnStatus: true, script: "${iisAppPool_script_path} ${iisAppPool_script_parameter} ")
		echo " iisAppPool_script_execute return code : ${output} " + currentTime()
        errorOnExit(output,'iisAppPool_script_execute ')
    }
	echo " Completed $action App Pool ${application_pool_name} - @ ${server_name} " + currentTime()
}

// start/stop IIS at remote server using powershell script (iisreset command)
def iisExecute_PS(action,remote_hosts,server_credentials){
	echo ":--- Performing $action - IIS @ ${remote_hosts} parallel ---:" + currentTime()
	def iis_service_script = libraryResource 'iis-service-script.ps1'
	writeFile file: 'iis-service-script.ps1', text: iis_service_script
	iis_service_script_path = ".\\iis-service-script.ps1"
	def hosts="$remote_hosts".split(",")
	def p_services = [:]
	for (int i=0; i<hosts.size(); i++)
	{
		def host = hosts[i]
		stage ("${action}@${host}"){
			p_services["@${host}_${action}"] = { 
					echo "@ ${host} - performing $action - IIS service " + currentTime()
					ansi_color_text("@ ${host} - performing $action - IIS service " + currentTime() , "info")
					withCredentials([usernamePassword(credentialsId: "$server_credentials", passwordVariable: 'server_password', usernameVariable: 'server_username')]){
						iis_service_script_parameter = "'${action}' '${host}' '${server_username}' '${server_password}'" 
						echo " iis_service_script_path : ${iis_service_script_path} ,,, iis_service_script_parameter : ${iis_service_script_parameter} "
						def output=powershell ( returnStatus: true, script: "${iis_service_script_path} ${iis_service_script_parameter} ")
						errorOnExit(output,'iis_service_script_execute_PS')
					}
					ansi_color_text("@ ${host} - completed $action - IIS service  " + currentTime(),"info")
			}
		}
	}
	parallel p_services
}

// start/stop  windows services @ remote server using powershell script 
def windowsService_PS(action,remote_hosts,server_credentials,service_name){
	echo ":--- Performing $action - service $service_name @ ${remote_hosts} parallel ---:" + currentTime()
	def windows_service_script = libraryResource 'windows-service-script.ps1'
  writeFile file: 'windows-service-script.ps1', text: windows_service_script
	windows_service_script_path = ".\\windows-service-script.ps1"
	def hosts="$remote_hosts".split(",")
	def p_services = [:]
	for (int i=0; i<hosts.size(); i++)
	{
		def host = hosts[i]
		stage ("${action}@${host}"){
			p_services["@${host}_${action}"] = { 
				echo "@ ${host} - performing $action - service $service_name  " + currentTime()
				withCredentials([usernamePassword(credentialsId: "$server_credentials", passwordVariable: 'server_password', usernameVariable: 'server_username')]){
					windows_service_script_parameter = "'${action}' '${host}' '${server_username}' '${server_password}' '${service_name}'" 
					echo " windows_service_script_path : ${windows_service_script_path} ,,, windows_service_script_parameter : ${windows_service_script_parameter} "
					def output=powershell ( returnStatus: true, script: "${windows_service_script_path} ${windows_service_script_parameter} ")
					errorOnExit(output,"${host} while executing script ${windows_service_script_path} ")
				}
				echo "@ ${host} - completed $action - service $service_name  " + currentTime()
				ansi_color_text("@ ${host} - completed $action - service $service_name  " + currentTime(),"info")
			}
		}
	}
	parallel p_services
}
