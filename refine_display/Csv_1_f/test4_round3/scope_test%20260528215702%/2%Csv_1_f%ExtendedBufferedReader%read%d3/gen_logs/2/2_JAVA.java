package org.apache.commons.csv;
import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_2_2Test {

    @Test
    void testRead_newLine() throws Exception {
        String input = "First line\nSecond line";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        int firstChar = reader.read();
        int secondChar = reader.read();
        
        Assertions.assertEquals('F', firstChar);
        Assertions.assertEquals('i', secondChar);
        
        // Read until the new line
        while (reader.read() != '\n') {}
        
        // Now we check if the lineCounter has increased
        Assertions.assertEquals(1, invokeGetLineNumber(reader));
    }

    @Test
    void testRead_carriageReturn() throws Exception {
        String input = "First line\rSecond line";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        // Read until the carriage return
        while (reader.read() != '\r') {}
        
        // Check if lineCounter has increased
        Assertions.assertEquals(1, invokeGetLineNumber(reader));
    }

    @Test
    void testRead_noNewLine() throws Exception {
        String input = "First line";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        while (reader.read() != -1) {}
        
        // Check if lineCounter remains zero
        Assertions.assertEquals(0, invokeGetLineNumber(reader));
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        int result = reader.read();
        
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        var method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        return (int) method.invoke(reader);
    }
}