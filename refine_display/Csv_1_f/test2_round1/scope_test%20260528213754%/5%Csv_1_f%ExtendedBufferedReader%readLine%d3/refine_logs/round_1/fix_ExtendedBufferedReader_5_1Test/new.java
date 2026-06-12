package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;

class ExtendedBufferedReader_5_1Test {

    @Test
    void testreadLine_normalCase() throws Exception {
        String input = "Hello, World!\nThis is a test.";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        String line2 = reader.readLine();

        Assertions.assertEquals("Hello, World!", line1);
        Assertions.assertEquals("This is a test.", line2);
    }

    @Test
    void testreadLine_emptyLine() throws Exception {
        String input = "\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line = reader.readLine();

        Assertions.assertEquals("", line);
    }

    @Test
    void testreadLine_endOfStream() throws Exception {
        String input = "";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line = reader.readLine();

        Assertions.assertNull(line);
    }

    @Test
    void testreadLine_lastCharSet() throws Exception {
        String input = "First Line\nSecond Line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        reader.readLine(); // Read first line
        String secondLine = reader.readLine(); // Read second line

        // Access private field lastChar using reflection
        java.lang.reflect.Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        int lastChar = (int) lastCharField.get(reader);

        Assertions.assertEquals('e', lastChar); // Last char of "Second Line"
    }

    @Test
    void testreadLine_lineCounterIncrement() throws Exception {
        String input = "Line 1\nLine 2\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        reader.readLine(); // Read first line
        reader.readLine(); // Read second line

        // Access private field lineCounter using reflection
        java.lang.reflect.Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        int lineCounter = (int) lineCounterField.get(reader);

        Assertions.assertEquals(2, lineCounter); // Should be 2 after reading two lines
    }

    @Test
    void testreadLine_boundaryConditions() throws Exception {
        String input = "\n\n"; // Two empty lines
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        String line2 = reader.readLine();
        String line3 = reader.readLine(); // Should be null

        Assertions.assertEquals("", line1);
        Assertions.assertEquals("", line2);
        Assertions.assertNull(line3);
    }

    @Test
    void testreadLine_mixedContent() throws Exception {
        String input = "First Line\n\nSecond Line\nThird Line\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        Assertions.assertEquals("First Line", reader.readLine());
        Assertions.assertEquals("", reader.readLine());
        Assertions.assertEquals("Second Line", reader.readLine());
        Assertions.assertEquals("Third Line", reader.readLine());
        Assertions.assertNull(reader.readLine()); // End of stream
    }
}