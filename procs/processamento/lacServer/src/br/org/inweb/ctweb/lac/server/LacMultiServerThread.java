package br.org.inweb.ctweb.lac.server;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.Socket;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LacMultiServerThread extends Thread {
	private Socket socket = null;
	private Lac lac = null;
	private Logger log = LoggerFactory.getLogger(LacMultiServerThread.class);
	
	public LacMultiServerThread(Socket socket, Lac lac){
		super("LacMultiserverThread");
		this.socket = socket;
		this.lac = lac;
		log.debug("LacMultiserverThread iniciado.");
	}
	
	public void run(){
		try{
			PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
			BufferedReader in = new BufferedReader(
									new InputStreamReader(socket.getInputStream()));
			String inputLine, outputLine;
			String contexto;
			String texto_instancia; 
			
			while((inputLine = in.readLine()) != null){
				String[] partes = inputLine.split("#");
				if (partes.length == 2){
					contexto = partes[0];
					texto_instancia = partes[1];
					outputLine = lac.classificar(contexto, texto_instancia);
					out.println(outputLine);
				} else {
					out.println("{\"status\": \"erro: formato incorreto\"}");
				}
			}
			out.close();
			in.close();
			socket.close();
			log.info("Cliente desconectou");
		} catch (Exception e) {
			log.error("Erro processando requisição", e);
		}
		
		
	}
}
