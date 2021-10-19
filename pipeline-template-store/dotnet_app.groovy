library 'shared-library'

// node_label : can be set during jenkins job initialization (dynamic pipeline service)  or pipeline yml store 
// jenkins_slave_label : can be set at pipeline store YML store & this can be override by App YML store file 
// buildsToKeep : can be set during jenkins job initialization (dynamic pipeline service) or pipeline yml store 
// timeoutMinutes : can be set at pipeline store YML store & this can be override by App YML store file 


// repo_host : can be set during jenkins job initialization (dynamic pipeline service) from webhook pay load  
// --- Below param can come from Developer YML file :
// SolutionName 
// Sonar_Project_Key
// app_branch
// Host_Name
// DCSE_Deploy_Credential
// Windows_Service_Name 
// Run_SonarQube
// Restore_Type
// Build_Type
// WSUnitTestProj 
// BuildOutputLocation

// --- Below param can come from org/dept/div level YML store :- 
// Sonar_Server_Name
// Sonar_MSBuild
// Sonar_Host_URL
// Sonar_Encoding
// Package_Type
// Nexus_URL
// Nexus_Version
// Nexus_Protocol
// Nexus_Repository
// Nexus_GroupID
// Nexus_Credential
// autoScheduleJob & schedule_job : can be set at App YML store / file based on needs 


node("$node_label") 
{
  if ("${env.jenkins_slave_label}" != 'null') 
  {
    agent_label = "$jenkins_slave_label"
  }
  if (env.buildsToKeep)
  {
    buildsToKeep_final= env.buildsToKeep
  }
  else
  {
    buildsToKeep_final= '50'
  }
}

pipeline {
	agent { 
		label "$agent_label"
	}
	environment {
		artifact_id = "${params.Environment_Type}-${params.Application_Name}"
		artifact_version = "${version}.${BUILD_NUMBER}"
		package_name = "${artifact_id}-${artifact_version}.${params.Package_Type}"
  }
	stages {
        // CI stages 
        stage('Continuous Integration ') {
            when {  expression { "$release" == 'CI' || "$release" == 'CI_CD'  }  }
            agent { label "$agent_label" }
            stages {
                // Stage to init -clean work space and JIRA approval check 
                stage('Initiation and JIRA check') {
                    steps {
                        // Validates the mandatory parameters required , clean workspace and other initialization activity for this pipeline template   
                        echo 'Pre build validation and clean up workspace '
                        deleteDir()
                        echo " --- Jenkins Template - integration_app.groovy --- "
                        jira_check()
                    }
                }
                //Stage to download the source code to Jenkins Build for compile/package
                stage('Checkout App Source Code') {
                    steps {
                        script {
                                scmCode.gitCheckOut(repo_host,app_branch,DCSE_GitTag_Credential)
                                echo "Completed App source checkout "
                            }
                    }
                }	
                // Stage to build the CBO code with Sonar Qube 	
                stage('Build and SonarQube Code Analysis') {
                    steps{
                        script{
                            codeAnalysis.execBuildAnalysis(Sonar_Server_Name,Sonar_MSBuild,Sonar_Project_Key,Sonar_Host_URL,Sonar_Encoding,SolutionName, Run_SonarQube, Restore_Type, Build_Type)
                        }
                    }
                }
                stage('Unit test application') {
                    when { expression{ "${UnitTest}" == 'yes' } }
                    steps{
                        script
                        {
                            inspection.unitTestApplication("${WSUnitTestProj}")
                        }
                    }
                }
                //Stage to Package the Artifacts
                stage('Package Deployment Artifacts') {
                    steps {
                        script {
                            // package artifacts with name 'package_name' and includes 'built code out put location folder ' 
                            dc_common.packageArtifactsAll(package_name, BuildOutputLocation)
                        }
                    }
                }
                //Stage to upload the packaged artifacts to Nexus Repository
                stage('Upload Deployment Artifact to Nexus ') {
                    steps {
                        script {
                            nexus.uploadArtifacts(artifact_id,artifact_version,package_name,"${params.Package_Type}","${params.Nexus_URL}","${params.Nexus_Version}","${params.Nexus_Protocol}","${params.Nexus_Repository}","${params.Nexus_GroupID}","${params.Nexus_Credential}")
                        }
                    }
                }
                // stage to stop all the services related to app for deployment 
                stage ('Stop IIS & Windows Services') {
                    steps {
                        script {
                            echo " Stop IIS & Windows Services "
                            // Stop DuckCreek service for config files deployment  
                            parallel(
                                duckcreek: {
                                    if( params.containsKey('IISStopStart') && "$IISStopStart" == 'yes' )  {
                                        echo " IIS Services Stop"
                                        winUtil.iisExecute_PS('stop',Host_Name,DCSE_Deploy_Credential)
                                    }
                                },
                                ws: {
                                    if( params.containsKey('WSStopStart') && "$WSStopStart" == 'yes' ) {
                                        echo " WS Services Stop"
                                        //awx.windowsServicesAWX(AnsInventory, AnsStopWSTemplate, Windows_Service_Name, AnsServerCredential)
                                        winUtil.windowsService_PS('stop',Host_Name,DCSE_Deploy_Credential,Windows_Service_Name)
                                    }
                                }
                            )
                            echo ' Completed Stop IIS & Windows Services '
                        }
                    }
                }
            }
        }
        // CD stages 
        stage('Continuous Deployment') {
            when {  expression {  "$release" == 'CD' || "$release" == 'CI_CD'  }  }
            agent { label "$agent_label" }
            stages {
                stage('Deployment of Package parallelly') {
                    parallel {
                        //Stage to deploy the artifacts on the actual server
                        stage ('Deploy components ') {
                            when { expression { "$CodeDeploy" == 'yes'  }  }
                            steps {
                                script {
                                    echo "Starting ${Application_Name} components deployment "
                                    //clearing destination directory
                                    echo " clearing destination directory in remote host[s] ${Host_Name} api location "
                                    dc_common.clear_dest_directory_ps(Host_Name,DCSE_Deploy_Credential,APILocation)
                                    // deploying package to destination remote host api location
                                    echo " deploying package to destination remote host[s] ${Host_Name} api location  "
                                    dc_common.deployPackage(Host_Name,DCSE_Deploy_Credential,APILocation,Environment_Type,Application_Name,artifact_version, package_name)
                                    echo "${Application_Name} components Deployment completed successfully"
                                }
                            }
                        }
                    }
                }
                // stage to start all the services related to app after deployment 
                stage ('Start IIS & Windows Services') {
                    steps {
                        script {
                            parallel(
                                duckcreek: {
                                    if( params.containsKey('IISStopStart') && "$IISStopStart" == 'yes' ) {
                                        echo " IIS Service Start"
                                        winUtil.iisExecute_PS('start',Host_Name,DCSE_Deploy_Credential)
                                    }
                                },
                                ws: {
                                    if( params.containsKey('WSStopStart') && "$WSStopStart" == 'yes' ) {
                                        echo " Windows Service Start"
                                        //awx.windowsServicesAWX(AnsInventory, AnsStartWSTemplate, Windows_Service_Name, AnsServerCredential)
                                        winUtil.windowsService_PS('start',Host_Name,DCSE_Deploy_Credential,Windows_Service_Name)
                                    }
                                }
                            )
                        }
                    }
                }
                //Stage to Execute SQL scripts 
                stage ('SQL Scripts execution') {
                    when {
                        expression { ( params.containsKey('SQLScriptRun')  && "$SQLScriptRun" == 'yes' ) }
                    }
                    steps {
                        script {

                            echo "Started Database files checkout : inside directory dbscript "
                            dir("dbscript") {
                                scmCode.gitCheckOutFolder(repo_host,app_branch,DCSE_GitTag_Credential,"Database")
                                echo "Completed Database checkout "
                        
                                echo " Started executing SQL scripts stage "
                                sqlUtil.executeSQLscripts(DBServerName,DBName,DCSE_DB_Credential,SQLScriptDirList)
                                echo " Completed execution of SQL scripts stage "
                                }
                        }
                    }
                }		
                // Stage to promote this current deployed build to higher environment ( auto update of build_number along with other params to other YML file)
                stage ('Code promotion : Update flofile YML ') {	
                    when {	
                        expression { params.containsKey('autoPromoteToNextEnv') && "$autoPromoteToNextEnv" == 'yes' }	
                    }	
                    steps {	
                        retry(3) {	
                            script {	
                                echo " branch_to_update:$branch_to_update , repo_host:$repo_host , repo credential:$DCSE_GitTag_Credential"
                                dc_common.updateOtherBranchYML(branch_to_update,repo_host,DCSE_GitTag_Credential)	
                            }	
                        }	
                    }
                }
            }
        }
	}
	options {
		timeout(time: "$timeoutMinutes", unit: 'MINUTES')   // timeout on whole pipeline job
		buildDiscarder(logRotator(numToKeepStr: env.branch == 'master' ? '' : "${buildsToKeep_final}"))
	}
	triggers {
		// @hourly(minute (0 - 59)) @dail(hour (0 - 23)) @Monthly(day of month (1 - 31)) @Yearly(month (1 - 12)) @Weekly(day of week (0 - 6) )
		parameterizedCron(env.autoScheduleJob == 'yes' ? """
		${schedule_job}
		""" : "")		
	}
	post {
		always {
			post_actions()
	  }
	}
}
