package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_9_4Test {

    @Test
    public void testGetComment_normalCase() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1", "value2"};
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals("This is a comment", record.getComment());
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1", "value2"};
        String comment = "";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals("", record.getComment());
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1", "value2"};
        String comment = null;
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertNull(record.getComment());
    }

    @Test
    public void testGetComment_withSpecialCharacters() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1", "value2"};
        String comment = "!@#$%^&*()_+";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals("!@#$%^&*()_+", record.getComment());
    }

    @Test
    public void testGetComment_withWhitespace() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1", "value2"};
        String comment = "   ";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals("   ", record.getComment());
    }

    @Test
    public void testGetComment_specialCharacterBoundary() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1", "value2"};
        String comment = "\u0000"; // Null character
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals("\u0000", record.getComment());
    }

    @Test
    public void testGetComment_veryLongComment() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1", "value2"};
        String comment = new String(new char[1000]).replace('\0', 'a'); // Long comment
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());
    }

    @Test
    public void testGetComment_boundaryValues() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1", "value2"};
        String comment = "Comment with boundary value: " + Integer.MAX_VALUE;
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());
    }

    @Test
    public void testGetComment_edgeCase() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1", "value2"};
        String comment = "Edge case comment with special chars: \uFFFF"; // Last unicode character
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());
    }
}