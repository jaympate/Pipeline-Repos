// Error handling method based on script execution return code  
def call(returnresult,message){
	if(returnresult != 0){            
		currentBuild.result = 'FAILED'
		// echo "return code : ${returnresult} : ERROR @ ${message} ---"  + currentTime()
		error_message = "return code : ${returnresult} : ERROR @ ${message} ---"  + currentTime()
		ansi_color_text(error_message,"error")
		// throw new RuntimeException("${message}")
		powershell " exit($returnresult) "         
	} 
}