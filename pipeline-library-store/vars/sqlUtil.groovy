
// method to execute SQL script at directories passed as comma separator ( .sql scripts will be executed in the order)
def executeSQLscripts(db_server_name,db_name,db_credentials,sql_directories_list){
  def dct_sql_script = libraryResource 'sql-wrapper-script.bat'
  writeFile file: 'sql-wrapper-script.bat', text: dct_sql_script
	dct_sql_script = ".\\sql-wrapper-script.bat"

  withCredentials([usernamePassword(credentialsId: "$db_credentials", passwordVariable: 'db_password', usernameVariable: 'db_username')]) {

    echo " Triggering db sql script : ${dct_sql_script} for each sql_directories $sql_directories_list "
    def sqlDir=sql_directories_list.split(",")
		for (int i=0; i<sqlDir.size(); i++) {
			def sql_Dir = sqlDir[i]
      dct_sql_script_parameters = " \"${db_server_name}\" \"${db_name}\" \"${db_username}\" \"${db_password}\" \"${sql_Dir}\" "
			echo " SQL scripts parameters : ${dct_sql_script_parameters}"
		  output = bat(script: "${dct_sql_script} ${dct_sql_script_parameters} ", returnStatus: true);
		  errorOnExit(output," executing SQL scripts @ ${db_server_name} - DB-name:${db_name} @ sql_Dir:${sql_Dir}")
      echo " Completed all SQL scripts at ${sql_Dir} "
		}
  }
}