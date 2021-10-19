def call()
{
  def default_jira_site="JIRA"
  def jira_site=(env.jira_siteName) ? "${jira_siteName}" : "${default_jira_site}"
  if (params.containsKey('jira_id') || params.containsKey('deploy_time')) 
  {
    def jira_status = ""
    def transitions = null
    if(params.containsKey('schema_version') && "${schema_version}" >= '1.3' && params.containsKey('slotEnable') && "${slotEnable}" == 'true' && "${release}" == 'deploy')
    {
      ansi_color_text("JIRA approval Skipped for this job","info")
    }
    else
    {		  
    ansi_color_text("JIRA approval required for this job","info")
    try {
	  // using jira-steps-plugin get jira details by ID
	   transitions = jiraGetIssue idOrKey: "${jira_id}", site: "${jira_site}"
	  // from jira details get jira status 
	   jira_status = transitions.data.fields.status.name.toString()
    }
    catch(error){
      ansi_color_text(" ${error}","error")
      def message="Error while getting jira issue, Please verify ${jira_id} is present and accessble"
      ansi_color_text("${message}","error")
      throw new Exception(error)
    }
    if (jira_status.equalsIgnoreCase("${workflow_new_status}")) 
    {
	    //if aproval jira meets the desired status 
	    withEnv(["JIRA_SITE=${jira_site}"]) 
		{
			try {
				jiraAddComment idOrKey: "${params.jira_id}", comment: "Build is scheduled for ${env.BUILD_URL}"
			}
			catch(error){
				ansi_color_text(" ${error}","error")
				def message="Build is scheduled for ${env.BUILD_URL}, Error while adding a comment to ${jira_id}"
				ansi_color_text("${message}","error")
			}
		}
    } 
    else 
    {
	  // this case is excuted if aproval jira is not in disired status to schedule a job 
      currentBuild.rawBuild.result = Result.ABORTED
      ansi_color_text("This Jira id: ${params.jira_id}  current work flo status is : ${jira_status}, so further script will not be executed","error")
      ansi_color_text("Expected Jira status is: ${workflow_new_status}","error")
      withEnv(["JIRA_SITE=${jira_site}"]) 
      {
	    try {
            jiraAddComment idOrKey: "${params.jira_id}", comment: "Build is scheduled for ${env.BUILD_URL} ,but aborted build because, lack of approval"
        }
		catch(err){
				ansi_color_text(" ${error}","error")
				def message="Build is scheduled for ${env.BUILD_URL} ,but aborted build because, lack of approval, Error while adding a comment to ${jira_id}"
				ansi_color_text("${message}","error")
	    }
	  }
      error('Skip-CI')
    }
  }
  }
  else
  {
    ansi_color_text("JIRA approal not required for this job","info")
  }
}
