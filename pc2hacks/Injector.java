import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.io.FileWriter;
import java.io.File;
import java.io.PrintWriter;

import edu.csus.ecs.pc2.core.InternalController;
import edu.csus.ecs.pc2.core.model.IInternalContest;
import edu.csus.ecs.pc2.core.model.InternalContest;
import edu.csus.ecs.pc2.core.model.ProblemDataFiles;
import edu.csus.ecs.pc2.core.model.Problem;
import edu.csus.ecs.pc2.core.model.Language;
import edu.csus.ecs.pc2.core.model.SerializedFile;
import edu.csus.ecs.pc2.core.model.ClientType;
import edu.csus.ecs.pc2.core.model.Filter;
import edu.csus.ecs.pc2.core.model.ClientId;
import edu.csus.ecs.pc2.core.model.ClientSettings;

import java.util.Date;
import java.text.DateFormat;
import java.text.SimpleDateFormat;

public final class Injector
{
	private SerializedFile valodator;
	private InternalController controller;
	private PrintWriter out;
	private int DEFAULT_SLEEP = 500;

	public static void main(String[] args)
	{
		new Injector(args);
	}
	public Injector(String[] args)
	{
		//Input reading
		InputStreamReader converter = new InputStreamReader(System.in);
		BufferedReader in = new BufferedReader(converter);

		//Prepare PC^2 internals
		IInternalContest model = new InternalContest();
		controller = new InternalController(model);

		try
		{
			//In case html directory is not there
			(new File("html")).mkdir();

			//Open html file for writing a list of problems
			FileWriter outFile = new FileWriter("html/problem_list.html");
			out = new PrintWriter(outFile);

			//Login to PC^2
			controller.setUsingMainUI(false);
			controller.start(args);
			controller.clientLogin(model, "root", "");

			//Add languages to PC^2
			Language langc = new Language("GNU C (added by valodator)");
			langc.setActive(true);
			langc.setCompileCommandLine("gcc -lm -o {:basename} {:mainfile}");
			langc.setProgramExecuteCommandLine("echo valodator");
			langc.setExecutableIdentifierMask("{:basename}");
			System.out.println("Adding C language");
			Thread.sleep(DEFAULT_SLEEP);

			Language langcpp = new Language("GNU C++ (added by valodator)");
			langcpp.setActive(true);
			langcpp.setCompileCommandLine("g++ -lm -o {:basename} {:mainfile}");
			langcpp.setProgramExecuteCommandLine("echo valodator");
			langcpp.setExecutableIdentifierMask("{:basename}");
			System.out.println("Adding C++ language");
			Thread.sleep(DEFAULT_SLEEP);

			Language langjava = new Language("Java (added by valodator)");
			langjava.setActive(true);
			langjava.setCompileCommandLine("javac {:mainfile}");
			langjava.setProgramExecuteCommandLine("echo valodator");
			langjava.setExecutableIdentifierMask("{:basename}.class");
			System.out.println("Adding java language");
			Thread.sleep(DEFAULT_SLEEP);

			controller.addNewLanguage(langc);
			controller.addNewLanguage(langcpp);
			controller.addNewLanguage(langjava);

			//Add judge and scoreboard account
			controller.generateNewAccounts(ClientType.Type.JUDGE.toString(),1,1,1,true);
			System.out.println("Adding judge account");
			Thread.sleep(DEFAULT_SLEEP);

			controller.generateNewAccounts(ClientType.Type.SCOREBOARD.toString(),1,1,1,true);
			System.out.println("Adding scoreboard account");
			Thread.sleep(DEFAULT_SLEEP);

			controller.generateNewAccounts(ClientType.Type.TEAM.toString(),1,20,1,true);
			System.out.println("Adding 20 team accounts");
			Thread.sleep(DEFAULT_SLEEP);

			/////
			//Read valodator.py
			valodator = new SerializedFile("./valodator.py");
			String CurLine;
			int numProblems=0;

			//Read input from user, and add problems
			Filter filter = new Filter();
			for(int i=0; (CurLine = in.readLine()) != null; i++)
			{
				CurLine = CurLine.trim();
				String link = getLink(CurLine);
				if(link != null)
				{
					//Add new problem to PC^2 and to problem_list.html
					char probLetter = (char)('A'+numProblems);
					Problem newproblem = addProblem(CurLine, "Problem "+probLetter);
					out.println( "<h2><a target=\"_blank\" href=\""+link+"\">Problem "+probLetter+"</a></h2>");
					numProblems++;

					//Add newproblem to be autojudged
					filter.addProblem(newproblem);

					//Sleeping
					System.out.println("Adding: " + CurLine +  "");
					Thread.sleep(DEFAULT_SLEEP);
				}
				else
				{
					System.out.println("Unreconized format <website>/<problem>: "+CurLine);
				}
			}
			//Assign new problems to judge1
			ClientId clientId = new ClientId(1, ClientType.Type.JUDGE, 1);
			ClientSettings judgesettings = new ClientSettings(clientId);
			judgesettings.setAutoJudging(true);
			judgesettings.setAutoJudgeFilter(filter);
			controller.updateClientSettings(judgesettings);

			//Add date and sign at the bottom of html
			DateFormat dateFormat = new SimpleDateFormat("yyyy/MM/dd HH:mm:ss");
			Date date = new Date();
			out.println("<br><hr>This list was generated automatically on " + dateFormat.format(date)
					+ " by <a href=\"http://github.com/emiraga/valodator\">valodator</a>.");
			out.close();
			System.out.println("Added " + numProblems +  " problems");
		}
		catch (Exception e)
		{
			e.printStackTrace();
			System.exit(1);
		}
		System.exit(0);
	}
	private String getLink(String code)
	{
		if(code.startsWith("livearchive/"))
			return "http://acmicpc-live-archive.uva.es/nuevoportal/data/problem.php?p="+code.substring(12);
		if(code.startsWith("spoj/"))
			return "http://www.spoj.pl/problems/"+code.substring(5);
		if(code.startsWith("tju/"))
			return "http://acm.tju.edu.cn/toj/showp"+code.substring(4)+".html";
		if(code.startsWith("timus/"))
			return "http://acm.timus.ru/problem.aspx?space=1&num="+code.substring(6);
		if(code.startsWith("uva/"))
		{
			String number = code.substring(4);
			if(number.length() > 2)
				return "http://acm.uva.es/problemset/v"+number.substring(0,number.length()-2)+"/"+number+".html";
		}
		return null;
	}
	public Problem addProblem(String code, String name)
	{
		Problem problem = new Problem(name);
		problem.setActive(true);
		problem.setShowValidationToJudges(false);
		problem.setTimeOutInSeconds(5);
		problem.setValidatedProblem(true);
		problem.setValidatorCommandLine("./{:validator} {:mainfile} {:resfile} " + code);
		problem.setHideOutputWindow(true);
		problem.setValidatorProgramName(code);
		problem.setShowCompareWindow(false);
		problem.setComputerJudged(true);
		problem.setManualReview(false);

		ProblemDataFiles problemdata = new ProblemDataFiles(problem);
		problemdata.setValidatorFile(valodator);

		controller.addNewProblem(problem, problemdata);
		return problem;
	}
}

