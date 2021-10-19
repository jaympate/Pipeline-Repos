// deploying the pacakge to remote hosts parallelly at specified location with pacakge_name using powershell script 
def deployPackage(deploy_hosts,deploy_credential,api_location, api_environment_type, api_application_name, api_artifact_version, api_package_name){
	def deployment_script = libraryResource 'DeploymentScriptLatest.ps1'
  writeFile file: 'DeploymentScriptLatest.ps1', text: deployment_script
	deployment_script_path = ".\\DeploymentScriptLatest.ps1"
	def hosts="$deploy_hosts".split(",")
	def deployments = [:]
	def nexus_artifact_url = "${Nexus_Protocol}://${Nexus_URL}/repository/${Nexus_Repository}/${Nexus_GroupID}/${api_environment_type}-${api_application_name}/${api_artifact_version}/${api_package_name}" 
	for (int i=0; i<hosts.size(); i++)
	{
		//echo "${hosts[i]}"
		def host = hosts[i]
		stage ("DEPLOY@${host}-${api_location}"){
			deployments["@${host}_${api_location}"] = { 

				echo "Started Deployment using powershell script @ deploy_host ${host} " + currentTime()			
				withCredentials([usernamePassword(credentialsId: "$deploy_credential", passwordVariable: 'password', usernameVariable: 'username')])
				{
					def deploy_script_parameters = "-nexus_artifact_url '${nexus_artifact_url}' -Application_Name '$Application_Name' -UserName '${username}' -Password '${password}' -Host_Name '$host' -dest_directory '${api_location}' -packageName '${api_package_name}'"
					echo "deploy_script_parameters :- ${deploy_script_parameters}"
					def output=powershell ( returnStatus: true, script: "${deployment_script_path} ${deploy_script_parameters} ")
					errorOnExit(output," ${host}_${api_location} deloyment package script ")
				}
				echo "Completed Deployment using powershell script @ deploy_host ${host}_${api_location} " + currentTime()

			}
		}
	}
	parallel deployments
}

// Run configurator utility with required config parameters to generate env spoecific config files and generate zip package file 
def run_configurator_ps(c_environment_name,c_product_list,c_output_dir,c_package_name){
	config_utility_exe = "${workspace}\\${script_dir}\\Chubb.DCSquare.Apps.ApplicationConfigurator\\Chubb.DCSquare.Apps.ApplicationConfigurator.exe"
	configurator_output_dir = "configoutput"

	echo " config_environment_name:${c_environment_name} , config_product_list :${c_product_list} " + currentTime()
	def c_product_names=c_product_list.split(",")
	for (int i=0; i<c_product_names.size(); i++) {
		c_product_name = c_product_names[i]
		def output = powershell ( returnStatus: true, script: "${config_utility_exe} '${c_environment_name}' '${c_product_name}' '${workspace}\\${config_dir}\\${config_template_dir}' '${workspace}\\${c_output_dir}' ") 
		errorOnExit(output,'error while generating config files [run_configurator_ps script] ')
	}
	echo " Completed generating config files from templates " + currentTime()

	echo " Started Packaging config files of ${c_output_dir}\\* - :${c_product_list}:" + currentTime()
	powershell "Compress-Archive ${workspace}\\${c_output_dir}\\${configurator_output_dir}\\* ${c_package_name} -Force"
	echo " Completed Packaging confg files :${c_product_list}:" + currentTime()
}


// Packaging with zip utility using 'package_name' param including specific folders @ param  'artifact_package_folders'
def packageDCArtifacts(package_name,artifact_package_folders){
	echo "Started Packaging artifacts"
	echo " package file : ${package_name} : package folders : ${artifact_package_folders}"
	bat """
		zip -r "${package_name}" ${artifact_package_folders}
	"""
	echo "Completed Packaging artifacts"
}

// Packaging using 'package_name' param with contents of all files under specified folder @ param 'BuildOutputLocation' not including parent folder
def packageArtifactsAll(package_name, BuildOutputLocation)
{
	echo "Started Packaging artifacts"
	powershell "Compress-Archive ${workspace}${BuildOutputLocation}\\* ${package_name} -Force"
	echo "Completed Packaging artifacts"
}

// Packaging duckcreek CBO artifacts using 'package_name' param with shared/bin , express/bin & web/bin dll files 
def packageDCArtifactsDLL(package_name,DLLOutputLocation,shared_bin_files,express_bin_files,web_bin_files){
	echo "Packaging CBO DLL artifacts"
	dc_package = "dcPackageOutput"
	shared_bin = "${workspace}\\${dc_package}\\Shared\\Bin"
	express_bin = "${workspace}\\${dc_package}\\Express\\Bin"
	web_bin = "${workspace}\\${dc_package}\\Web\\Bin"

	dll_output_location = "${workspace}\\${DLLOutputLocation}\\*"

	echo "Create folder '${shared_bin}' for SharedBin contents and copy DLL's [${shared_bin_files}] to be placed in Shared Bin "
	powershell "New-Item ${shared_bin} -ItemType Directory "
	powershell "Copy-Item -Path ${dll_output_location} -Include ${shared_bin_files} -Destination ${shared_bin} -Force"


	echo "Create folder ${express_bin} for ExpressBin contents and copy DLL's [${express_bin_files}] to be placed in Express Bin"
	powershell "New-Item ${express_bin} -ItemType Directory "
	powershell "Copy-Item -Path ${dll_output_location} -Include ${express_bin_files} -Destination ${express_bin} -Force"
					
	echo "Create folder ${web_bin} for WebBin contents and copy DLL's [${web_bin_files}] to be placed in Web Bin"
	powershell "New-Item ${web_bin} -ItemType Directory "
	powershell "Copy-Item -Path ${dll_output_location} -Include ${web_bin_files} -Destination ${web_bin} -Force"

	echo "Packaging the output folder that has shared/bin,express/bin & web/bin contents"
 	powershell "Compress-Archive ${workspace}\\${dc_package}\\* ${package_name} -Force"

}

// Checkout other branch YML file and update YML file ( build_number, app version , app_branch along with other params then check in the file
def updateOtherBranchYML(branch_to_update,repo_host,repo_credential){
	def flo_file_to_update = "flo_${branch_to_update}.yml"
	echo " Auto Promote current deployed code by updating flow file ${flo_file_to_update} of env branch ${branch_to_update} "
	echo " Current jenkins successful build number= ${BUILD_NUMBER} will be updated "
	echo " Current branch flow file mandatory params ... version=${version}; app_branch=${app_branch} ;Environment-Type=${Environment_Type},  "
	echo ("Current branch flow file other params - AgentDeploy=${AgentDeploy}, UnderWriterDeploy=${UnderWriterDeploy} "
				+ " , ConfigDeploy=${ConfigDeploy}, ConfigDeploy_UW=${ConfigDeploy_UW}; ")		
	
	dir("$branch_to_update"){
		echo "Start checkout branch to update - $branch_to_update from git repo url - $repo_host "
		git branch: "$branch_to_update", changelog: false, url: "$repo_host"				
		echo 'Completed branch checkout from Git'
		echo "Checking if the YML file exists.."		
		bat "dir ${workspace}\\${branch_to_update}"
		File file = new File("${workspace}//${branch_to_update}//${flo_file_to_update}")
		println "path to the file: ${workspace}\\${branch_to_update}\\${flo_file_to_update}"
		println file.exists()
		println file.isDirectory()
		/*try {
			if(!file.exists()) {
				echo "YML file $file not found.."
				sleep(5)
			}
		}*/
		echo "Finished Checking if the YML file exists.."
		def update_yml_script = libraryResource 'UpdateFlowFile.ps1'
  		writeFile file: 'UpdateFlowFile.ps1', text: update_yml_script
		def update_yml_script_path = ".\\UpdateFlowFile.ps1"

		def update_yml_script_path_parameters = ("-YMLFile ${workspace}\\${branch_to_update}\\${flo_file_to_update} "
		+ "-Build_Number ${BUILD_NUMBER} -version ${version} -app_branch ${app_branch}  -Environment_Type ${Environment_Type} "
		+ "-Agent_Deploy ${AgentDeploy} -Under_Writer_Deploy ${UnderWriterDeploy} -Config_Deploy ${ConfigDeploy} "
		+ "-Config_Deploy_UW ${ConfigDeploy_UW}")

		echo "update_yml_script_path_parameters --- ${update_yml_script_path_parameters} "
		def output=powershell ( returnStatus: true, script: "${update_yml_script_path} ${update_yml_script_path_parameters} ")
		errorOnExit(output,'update yml script ')	

		// update config to avoid warning like "LF will be replaced by CRLF" during commit command.		
		bat "git config --global core.safecrlf false"
		bat "git add ${flo_file_to_update}"			   
		bat 'git commit -m "Updating the build_number:%BUILD_NUMBER% ,version:%version% ,app_branch:%app_branch%, Environment_Type:%Environment_Type% in the flo file"'
		
		echo "Pushing the changes to gitHub.."				
		withCredentials([usernamePassword(credentialsId: "$repo_credential", passwordVariable: 'password', usernameVariable: 'username')])
		{
			def repo_host_temp = "$repo_host".substring(8)
			bat "git branch --set-upstream-to ${branch_to_update}"							
			bat "git push https://${username}:${password}@${repo_host_temp}"
		}
		echo "Push the changes to gitHub.."	
		
	}
}

def clear_dest_directory_ps(deploy_hosts,deploy_credential,api_location){
	def hosts="$deploy_hosts".split(",")
	def deployments = [:]
	for (int i=0; i<hosts.size(); i++)
	{
		def host = hosts[i]
		stage ("CLEAR@${host}-${api_location}"){
			deployments["@${host}_${api_location}"] = { 
				echo "Started clearing destination directory using powershell script @ deploy_host ${host} " + currentTime()			
				withCredentials([usernamePassword(credentialsId: "$deploy_credential", passwordVariable: 'password', usernameVariable: 'username')])
				{
					def output=powershell (returnStatus: true, script: """
					try
					{
						\$api_location = "${api_location}"
						#Creates session object based on username and password
						\$vm_SecurePass = ConvertTo-SecureString -AsPlainText ${password} -Force -ErrorAction stop
						\$Cred = New-Object System.Management.Automation.PSCredential -ArgumentList aceina\\"${username}",\$vm_SecurePass -ErrorAction stop
						\$sess = New-PSSession -computerName ${host} -Credential \$Cred -ErrorAction stop
						echo "started cleaning directory"
						echo \$api_location
						Invoke-Command -Session \$sess -ErrorAction Stop -Command {
							Param(\$dest_directory)
							Get-ChildItem -path \$dest_directory -Recurse -Force | remove-item -Recurse -Force
						} -ArgumentList \$api_location
						echo "completed cleaning directory"
					} 
					catch {
    						Write-Host "ERROR in REMOTEHOST  @ \$_.exception.message" 
						exit 1
					}
					finally{
						echo 'Completed clearing destination directory on remote server'
						Remove-PSSession \$sess
					}
					""")
					errorOnExit(output," ${host} clear destination folder method ")
				}
				echo "Completed clearing destination directory using powershell script @ deploy_host ${host} " + currentTime()
			}
		}
    parallel deployments
	}
}

