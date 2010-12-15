import edu.csus.ecs.pc2.core.InternalController;
import edu.csus.ecs.pc2.core.model.IInternalContest;
import edu.csus.ecs.pc2.core.model.InternalContest;

public final class Starter
{
  public static void main(String[] args)
  {
    IInternalContest model = new InternalContest();
    InternalController controller = new InternalController(model);
	
	//this line is the only reason for having this Starter.java
    controller.setContestPassword("site1");

    if ((args.length > 0) && (args[0].equals("--team1")))
      try {
        controller.setUsingMainUI(false);
        controller.start(args);

        controller.clientLogin(model, "t1", "");
      }
      catch (Exception e) {
        e.printStackTrace();
      }
    else
      controller.start(args);
  }
}
