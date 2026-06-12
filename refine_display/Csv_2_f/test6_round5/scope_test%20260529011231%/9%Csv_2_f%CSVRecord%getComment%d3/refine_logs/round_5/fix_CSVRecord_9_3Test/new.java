package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_9_3Test {

    @Test
    public void testGetComment_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals("This is a comment", csvRecord.getComment());
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "";
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals("", csvRecord.getComment());
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals(null, csvRecord.getComment());
    }

    @Test
    public void testGetComment_specialCharacters() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "!@#$%^&*()_+";
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals("!@#$%^&*()_+", csvRecord.getComment());
    }

    @Test
    public void testGetComment_boundaryValues() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = " ";
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals(" ", csvRecord.getComment());
    }

    @Test
    public void testGetComment_largeComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = new String(new char[1000]).replace('\0', 'a'); // Large comment
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals(comment, csvRecord.getComment());
    }

    @Test
    public void testGetComment_whitespaceComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "    "; // Whitespace comment
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals("    ", csvRecord.getComment());
    }
}