/*
Post actoins 
*/
def call(){
script{
def default_jira_site="JIRA"
def jira_site=(env.jira_siteName) ? "${jira_siteName}" : "${default_jira_site}"
def build_number = "${currentBuild.number}"
def metadata_repo = "dynaflo-metadata"
if (params.containsKey('BUILD_NUMBER')) {
	build_number = "${params.BUILD_NUMBER}"
}

nexus_mfy_repo = (env.nexus_mfy_repo) ? "${nexus_mfy_repo}" : "${metadata_repo}"
artifact_repository = (env.override_artifact_repository) ? "${override_artifact_repository}" : "${artifact_repository}"	
writeFile file: "$WORKSPACE/${artifact_no_ext}-${version}.${build_number}.MFY", text: "source_path: http://${nexus_url}/repository/${artifact_repository}/${organization}/${artifact_no_ext}/${version}.${build_number}/${artifact_no_ext}-${version}.${build_number}-${classifier}.${source_env}.${artifact_ext}\nstatus: ${currentBuild.currentResult}" 
try{
nexusArtifactUploader artifacts: [[artifactId: "${artifact_no_ext}", classifier: '', file: "${artifact_no_ext}-${version}.${build_number}.MFY", type: 'MFY']], credentialsId: 'dynaflo-nexus', groupId: "${environment}/${organization}", nexusUrl: "${nexus_url}", nexusVersion: 'nexus3', protocol: 'http', repository: "${nexus_mfy_repo}", version: "${version}.${build_number}"
}
catch(err){
	ansi_color_text("Error while uploading mfy file to ${nexus_url}","error")
	ansi_color_text("Please verify nexus url, credentials and required aurguments","error")
	error(err.toString())
}

if(params.containsKey('jira_id'))
	{
		// buildlog_attachment()
						
		withEnv(["JIRA_SITE=${jira_site}"]) {
				try{
    			jiraAddComment idOrKey: "${params.jira_id}", comment: "deploy completed as ${currentBuild.currentResult}, Build Number : ${build_number}, Version : ${params.version}, Artifact: http://${params.nexus_url}/repository/${nexus_mfy_repo}/${params.organization}/${params.artifact_no_ext}/${params.version}.${build_number}/${params.artifact_no_ext}-${params.version}.${build_number}-${params.classifier}.${params.source_env}.${params.artifact_ext}"
				}
				catch(err){
				def message="deploy completed as ${currentBuild.currentResult}, Error while adding a comment to ${params.jira_id}"
				ansi_color_text("${message}","error")

				}
			// jiraUploadAttachment file: 'build.log', idOrKey: "${params.jira_id}"
    		}

		try{
		mail_users_list = approver_details_from_jira("${jira_url}","${jira_auth}","${jira_id}","${workflow_new_status}","${mail_users_list}")
		}
		catch(err){
		ansi_color_text("Error while getting approver details from jira ","error")
		ansi_color_text(err.toString(),"error")
		throw new Exception(err)
		}
		buildlog_attachment()
		try{	
		nexusArtifactUploader artifacts: [[artifactId: "${params.artifact_no_ext}", classifier: '', file: "$WORKSPACE/build.log", type: 'log']], credentialsId: 'dynaflo-nexus', groupId: "${params.environment}/${params.organization}", nexusUrl: "${params.nexus_url}", nexusVersion: 'nexus3', protocol: 'http', repository: "${nexus_mfy_repo}", version: "${params.version}.${build_number}"
    	}
		catch(err){
		ansi_color_text("Error while uploading build log to nexus ","error")
		ansi_color_text(err.toString(),"error")
		throw new Exception(err)
		}
		}
		
		dynaflo_swapapi_callback_v1()
}

script{
        if (params.containsKey('group') && "${group}" == "true" && params.containsKey('parent_cid')){
            echo "This Job notification will get from group deploy job"
        }else{
	  emailext ( subject: '${JOB_NAME} ${build_number} Result:${BUILD_STATUS} ', from: "${jenkins_from_mail}", attachLog: true, compressLog: true, body: '''${SCRIPT, template="groovy-html.template"} <html><head></head><body><div><p class=MsoNormal><span style='font-size:10.0pt;font-family:"Georgia",serif'>Regards,<o:p></o:p></span></p><p class=MsoNormal><img width=100 height=10 style='width:1.0416in;height:.1083in' id="_x0000_i1026" src="http://www.chubb.com/common/images/CHUBB_Logo_Purple.png" alt="Chubb Logo"><br><br><b><span style='font-size:10.0pt;font-family:"Georgia",serif;color:black'>DevOps Support</span></b><span style='font-size:10.0pt;font-family:"Georgia",serif;color:black'><br>Digital DevOps<br>Jenkins Prod <br><o:p></o:p></p><a href="mailto:DIO_Support@chubb.com?Subject=Support on Jenkins" target="_top">Need Support</a></span></div></body></html>''', mimeType: 'text/html', to: "${mail_users_list}")
         }
}
 script{
           if (currentBuild.currentResult == "FAILURE"){
               //logstashSend failBuild: false, maxLines: -1	       
		try{
		     // (13-Oct-2020) [DDO-3241] removed stageName from arguments list.
		     write2sentry("${WORKSPACE}","${environment}","${repo_host}","${BUILD_NUMBER}","${JOB_URL}","${cid}","${jenkins_branch}")
		  }
	       catch(err){
	             ansi_color_text("Error while writing event to sentry ","warning")
		     ansi_color_text(err.toString(),"warning")
	         }
           }
       }

}
