package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;
import java.io.IOException;
import java.lang.reflect.Method;

class ExtendedBufferedReader_2_3Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        int firstChar = reader.read();
        int secondChar = reader.read();
        
        Assertions.assertEquals('H', firstChar);
        Assertions.assertEquals('e', secondChar);
    }

    @Test
    void testRead_newLine() throws Exception {
        String input = "Hello\r\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        reader.read(); // Read 'H'
        reader.read(); // Read 'e'
        reader.read(); // Read 'l'
        reader.read(); // Read 'l'
        int newLineChar = reader.read(); // Read '\r'
        
        Assertions.assertEquals('\r', newLineChar);
        
        // Verify line counter increment
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        int lineNumber = (int) getLineNumberMethod.invoke(reader);
        
        Assertions.assertEquals(1, lineNumber);
        
        reader.read(); // Read 'W'
        int nextChar = reader.read(); // Read 'o'
        Assertions.assertEquals('o', nextChar);
        
        lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(1, lineNumber);
        
        nextChar = reader.read(); // Read 'r'
        Assertions.assertEquals('r', nextChar);
        
        lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(1, lineNumber);
        
        nextChar = reader.read(); // Read 'l'
        Assertions.assertEquals('l', nextChar);
        
        lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(1, lineNumber);
        
        nextChar = reader.read(); // Read 'd'
        Assertions.assertEquals('d', nextChar);
        
        lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(1, lineNumber);
        
        nextChar = reader.read(); // Read end of stream
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, nextChar);
    }

    @Test
    void testRead_multipleLines() throws Exception {
        String input = "Line1\nLine2\nLine3";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        reader.read(); // Read 'L'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        reader.read(); // Read '1'
        reader.read(); // Read '\n'
        
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        int lineNumber = (int) getLineNumberMethod.invoke(reader);
        
        Assertions.assertEquals(1, lineNumber);
        
        reader.read(); // Read 'L'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        reader.read(); // Read '2'
        reader.read(); // Read '\n'
        
        lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(2, lineNumber);
        
        reader.read(); // Read 'L'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        reader.read(); // Read '3'
        
        lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(3, lineNumber);
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "Hello";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        while (reader.read() != ExtendedBufferedReader.END_OF_STREAM) {
            // Read until the end
        }
        
        int endOfStream = reader.read();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, endOfStream);
    }

    @Test
    void testRead_lineBreaks() throws Exception {
        String input = "Hello\rWorld\n!";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        reader.read(); // Read 'H'
        reader.read(); // Read 'e'
        reader.read(); // Read 'l'
        reader.read(); // Read 'l'
        reader.read(); // Read 'o'
        int carriageReturn = reader.read(); // Read '\r'
        
        Assertions.assertEquals('\r', carriageReturn);
        
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        int lineNumber = (int) getLineNumberMethod.invoke(reader);
        
        Assertions.assertEquals(1, lineNumber);
        
        reader.read(); // Read 'W'
        reader.read(); // Read 'o'
        reader.read(); // Read 'r'
        reader.read(); // Read 'l'
        reader.read(); // Read 'd'
        int newLine = reader.read(); // Read '\n'
        
        Assertions.assertEquals('\n', newLine);
        
        lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(2, lineNumber);
        
        reader.read(); // Read '!'
        int endOfStream = reader.read();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, endOfStream);
    }
}