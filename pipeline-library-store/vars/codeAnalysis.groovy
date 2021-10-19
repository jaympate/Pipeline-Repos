
// Code analysis with Sonar Qube analysis server 
def execSonarQubeAnalysis(Sonar_Server_Name,Sonar_MSBuild,Sonar_Project_Key,Sonar_Host_URL,Sonar_Encoding,SolutionName){
	withSonarQubeEnv("${Sonar_Server_Name}")
	{
		echo 'Starting Build and SonarQube analysis'
		bat "${Sonar_MSBuild} begin /k:${Sonar_Project_Key} /d:sonar.host.url=${Sonar_Host_URL} /v:sonar.projectVersion=1.0 /d:sonar.sourceEncoding=${Sonar_Encoding}"
		bat "NuGet restore ${SolutionName}"
		bat "MSBuild ${SolutionName} /p:Configuration=Release"
		bat "${Sonar_MSBuild} end"
		echo 'Checking SonarQube analysis status..'
		echo 'Completed SonarQube analysis'
	}
}

// build code with Build tyle 
def execBuildAnalysis(Sonar_Server_Name,Sonar_MSBuild,Sonar_Project_Key,Sonar_Host_URL,Sonar_Encoding,SolutionName, Run_SonarQube, Restore_Type, Build_Type)
{
	withSonarQubeEnv("${Sonar_Server_Name}")
	{
		echo 'Starting Build and SonarQube analysis'
		if("${Run_SonarQube}" == 'yes'){
			bat "${Sonar_MSBuild} begin /k:${Sonar_Project_Key} /d:sonar.host.url=${Sonar_Host_URL} /v:sonar.projectVersion=1.0 /d:sonar.sourceEncoding=${Sonar_Encoding}"
		}
		bat "${Restore_Type} restore ${SolutionName}"
		bat "${Build_Type} ${SolutionName} /p:Configuration=Release"
		if("${Run_SonarQube}" == 'yes'){
			bat "${Sonar_MSBuild} end"
		}
		echo 'Completed Build & SonarQube analysis'
	}
}

// utility to evaluate Manuscripts for errors, or potential problems and produces either XML, or HTML output
def execMSCOP(msRoot,msCatalogPath,msoutputRoot,msxslRoot)
{
	def mscop_script = "${script_dir}\\MsCop\\CommandLine\\MsCop.ps1"
	def mscop_merge_script = "${script_dir}\\MsCop\\CommandLine\\MsCopXmlMerge.ps1"
	echo "Start execution of MsCop analysis"
  def mscop_script_parameters = "-manuscriptRoot '${msRoot}' -MSCatalogPath '${msCatalogPath}' -xslRoot '${script_dir}\\${msxslRoot}' -outputRoot '${msoutputRoot}' "
	echo "mscop_script_parameters :- ${mscop_script_parameters}"
	powershell(returnStatus : true,script:"${mscop_script} ${mscop_script_parameters}")
	powershell(returnStatus : true,script:"${mscop_merge_script} -reviewFolder '${msoutputRoot}\\XML'")
	zip dir: "${msoutputRoot}\\XML", glob: "Merged*.xml", zipFile: "MSCoplogs-XML.zip"
	zip dir: "${msoutputRoot}\\HTML", glob: "", zipFile: "MSCoplogs_HTML.zip"
	echo 'Completed MsCop analysis & MSCoplogs-XML.zip , MSCoplogs_HTML.zip zip files are created'
}

def notificationMSCop(zipfile,notification_list){
	emailext attachLog: true, attachmentsPattern: "${zipfile}", 
	body: """Hi Team,\t PFA the MsCop analysis report XML and HTML format for your reference.
	\nJenkins Job URL: ${BUILD_URL} \nRegards, \nDCSquareDevOpsTeam.\nNote: This is an auto-generated email, please do not respond to this thread. If you have any questions, please reach dcsquaredevops@chubb.com
	""", subject: "MsCop Analysis of ${JOB_NAME} ", from: "${jenkins_from_mail}" , to: "${notification_list}"
}