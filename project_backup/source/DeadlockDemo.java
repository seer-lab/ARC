import java.util.*;

public class DeadlockDemo {
    private final static Object lock1 = new Object ();
    private final static Object lock2 = new Object ();
    private static Random random = new Random ();
    final static int SLEEP = 100;
    final static int NUM = 2;
    static Integer raceVar = null;

    static void sleep (int millis) {
        try {
            Thread.sleep (millis);
        } catch (InterruptedException exc) {
            throw new RuntimeException ("unexpected interrupt");
        }
    }

    static void randomSleep () {
        sleep (random.nextInt (SLEEP));
    }

    public static void main (String [] args) {
        System.out.println ("Starting");
        sleep (1000);
        Agent1 [] agents1 = new Agent1 [NUM];
        Agent2 [] agents2 = new Agent2 [NUM];
        for (int i = 0;
        i < NUM; i ++) {
            agents1 [i] = new Agent1 (1);
            agents2 [i] = new Agent2 (1);
        }
        for (int i = 0;
        i < NUM; i ++) {
            agents1 [i].start ();
            System.out.println (" starting agent1");
            randomSleep ();
            agents2 [i].start ();
            System.out.println (" starting agent2");
            randomSleep ();
        }
    }

    private static class Agent1 extends Thread {
        int counter;

        Agent1 (int i) {
            counter = i;
        }

        public void run () {
            System.out.println ("agent1 started");
            this.work ();
        }

        public void work () {
            if (raceVar == null) {
                raceVar = new Integer (10);
            }
            for (int i = 0;
            i < counter; i ++) {
                randomSleep ();
                synchronized (lock1) {
                    System.out.println ("  --- Synchronize 1 --- AGENT1-" + Thread.currentThread ().getName () + " got lock1");
                    randomSleep ();
                    synchronized (lock2) {
                        System.out.println ("  --- Synchronize 2 --- AGENT1-" + Thread.currentThread ().getName () +
                          " got lock2");
                        randomSleep ();

                    }
                    System.out.println ("Room for sync 2 to expand down");

                }
                System.out.println ("  AGENT --1--" + Thread.currentThread ().getName () + " released locks");
            }
        }

    }

    private static class Agent2 extends Thread {
        int counter;

        Agent2 (int i) {
            counter = i;
        }

        public void run () {
            System.out.println ("agent2 started");
            this.work ();
        }

        public void work () {
            if (raceVar == null) {
                raceVar = new Integer (20);
            }
            for (int i = 0;
            i < counter; i ++) {
                randomSleep ();
                synchronized (this) {
                    synchronized (this) {
                        synchronized (this) {
                            /* MUTANT : "ASAS (Added Sync Around Sync)" */
                            synchronized (this) {
                                synchronized (lock2) {
                                    System.out.println ("  --- Synchronize 3 --- AGENT2-" + Thread.currentThread ().getName () +
                                      " got lock2");
                                    randomSleep ();
                                    synchronized (lock1) {
                                        System.out.println ("  --- Synchronize 4 --- AGENT2-" + Thread.currentThread ().getName
                                          () + " got lock1");
                                        randomSleep ();

                                    }
                                    System.out.println ("Room for sync 4 to expand down");

                                }
                                }
                                /* MUTANT : "ASAS (Added Sync Around Sync)" */

                            }

                        }

                    }
                    System.out.println ("  AGENT --2--" + Thread.currentThread ().getName () + " released locks");
                }
            }

        }

    }

