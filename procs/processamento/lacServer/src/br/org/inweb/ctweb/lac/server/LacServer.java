package br.org.inweb.ctweb.lac.server;

import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.net.ServerSocket;

import javax.management.MBeanServer;
import javax.management.ObjectName;

import org.apache.commons.cli.BasicParser;
import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.HelpFormatter;
import org.apache.commons.cli.Options;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import weka.classifiers.rules.LACFeatureIndex;
import br.org.inweb.ctweb.lac.mbean.LacMBean;
import br.org.inweb.ctweb.lac.mbean.LacMBeanImpl;

public class LacServer {
	public static void main(String[] args) throws Exception{
		final Logger log = LoggerFactory.getLogger(LacServer.class);
		int port = 4444;
		ServerSocket serverSocket = null;
		boolean listening = true;
		
		//Le e faz parse da opcoes
		Options options = new Options();
		options.addOption("m", true, "Tamanho máximo da regra");
		options.addOption("s", true,"Suporte mínimo para itemsets  [0.0-1.0] (relativo ao tam da base)");
		options.addOption("c", true, "Confiança mímina para suportar a regra [0.0-1.0]");
		options.addOption("i", true, "Arquivo com os nomes dos treinos");
		options.addOption("p", true, "Porta");
		options.addOption("b", true, "Diretório base onde estão os arquivos de treino. Usado quando o arquivo com os nomes de treinos usa caminhos relativos.");
		options.addOption("d", false, "Debug Mode");
		options.addOption("x", false, "Não usar ngramas");
		options.addOption("h", false, "Ajuda");
		
		BasicParser parser = new BasicParser();
		CommandLine cl = parser.parse(options, args);
		
		if (cl.hasOption("h") || !(cl.hasOption('s') &&
									cl.hasOption("m") &&
									cl.hasOption("c") &&
									cl.hasOption("i") &&
									cl.hasOption("p"))){
			new HelpFormatter().printHelp("java -cp CLASSPATH " + LacServer.class.getCanonicalName(), options);
			System.exit(1);
		}
		
		float suporte = Float.parseFloat(cl.getOptionValue("s"));
		float confianca = Float.parseFloat(cl.getOptionValue("c"));
		String inputFile = cl.getOptionValue("i");
		String baseDir = cl.getOptionValue("b");
		if (baseDir == null){
			baseDir = ".";
		}
		boolean debug = cl.hasOption("d");
		int tam_regras = Integer.parseInt(cl.getOptionValue("m"));
		port = Integer.parseInt(cl.getOptionValue("p"));
		
		if (suporte > .4){
			log.warn("Suporte ({}) maior que 40%? Verificar", suporte); 
		}
		if (confianca > .1){
			log.warn("Confiança ({}) maior que 10%? Verificar", confianca); 
		}
		//constroi classficadores
		Lac lac = new Lac(baseDir, inputFile, tam_regras - 1, suporte, confianca, false,
				debug, new LACFeatureIndex(), cl.hasOption("x"));
		

		//MBean usado para administração. Ver JXM e jconsole
		MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
		ObjectName name = new ObjectName(LacMBean.class.getPackage().getName() + ":type=LacMBean");
		LacMBeanImpl mbean = new LacMBeanImpl(lac);
		mbs.registerMBean(mbean, name);

		log.info("Servidor LAC executando - porta {}\n  Usando arquivo de treinos {}", port, inputFile);
		log.info("Treinos disponíveis: {}", lac.getTrainsName());
		try{
			serverSocket = new ServerSocket(port);
		} catch(IOException e){
			throw new LacServerException(e);
		}
		
		//pra cada conexao, cria uma instancia de LacMutltiServerThread
		while(listening){
			new LacMultiServerThread(serverSocket.accept(), lac).start();
		}
		serverSocket.close();
	}
}
