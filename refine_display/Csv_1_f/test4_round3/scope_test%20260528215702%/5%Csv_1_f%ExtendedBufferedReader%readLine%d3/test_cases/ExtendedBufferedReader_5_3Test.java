package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

class ExtendedBufferedReader_5_3Test {

    @Test
    void testReadLine_normalCase() throws Exception {
        String input = "Hello World\nThis is a test";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        String line1 = reader.readLine();
        Assertions.assertEquals("Hello World", line1);
        
        String line2 = reader.readLine();
        Assertions.assertEquals("This is a test", line2);
        
        String line3 = reader.readLine();
        Assertions.assertNull(line3);
        
        // Verify the internal state
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        Assertions.assertEquals(2, getLineNumberMethod.invoke(reader));
    }

    @Test
    void testReadLine_emptyLine() throws Exception {
        String input = "\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        String line = reader.readLine();
        Assertions.assertEquals("", line);
        
        // Verify the internal state
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        Assertions.assertEquals(1, getLineNumberMethod.invoke(reader));
        
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, lastCharField.get(reader));
    }

    @Test
    void testReadLine_endOfStream() throws Exception {
        String input = "";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        String line = reader.readLine();
        Assertions.assertNull(line);
        
        // Verify the internal state
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, lastCharField.get(reader));
        
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        Assertions.assertEquals(0, getLineNumberMethod.invoke(reader));
    }

    @Test
    void testReadLine_multipleLines() throws Exception {
        String input = "Line 1\nLine 2\nLine 3";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        Assertions.assertEquals("Line 1", reader.readLine());
        Assertions.assertEquals("Line 2", reader.readLine());
        Assertions.assertEquals("Line 3", reader.readLine());
        Assertions.assertNull(reader.readLine());
        
        // Verify the internal state
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        Assertions.assertEquals(3, getLineNumberMethod.invoke(reader));
    }

    @Test
    void testReadLine_boundaryValues() throws Exception {
        String input = "\n\n\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        Assertions.assertEquals("", reader.readLine());
        Assertions.assertEquals("", reader.readLine());
        Assertions.assertEquals("", reader.readLine());
        Assertions.assertNull(reader.readLine());
        
        // Verify the internal state
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        Assertions.assertEquals(3, getLineNumberMethod.invoke(reader));
        
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, lastCharField.get(reader));
    }

    @Test
    void testRead_singleCharacter() throws Exception {
        String input = "A";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        int result = reader.read();
        Assertions.assertEquals('A', result);
        
        result = reader.read();
        Assertions.assertEquals(-1, result); // end of stream
        
        // Verify the internal state
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, lastCharField.get(reader));
    }

    @Test
    void testReadAgain() throws Exception {
        String input = "Hello";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        reader.read(); // Read first character
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        int result = (int) readAgainMethod.invoke(reader);
        
        Assertions.assertEquals('e', result);
        
        // Verify the internal state
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        Assertions.assertEquals('e', lastCharField.get(reader));
    }

    @Test
    void testLookAhead() throws Exception {
        String input = "Look Ahead";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        Method lookAheadMethod = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        lookAheadMethod.setAccessible(true);
        int result = (int) lookAheadMethod.invoke(reader);
        
        Assertions.assertEquals('L', result);
        
        // Verify the internal state
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, lastCharField.get(reader)); // lastChar should not change
    }
}