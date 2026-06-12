package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_9_2Test {

    @Test
    public void testGetComment_normalCase() throws Exception {
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        String comment = "This is a comment";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals(comment, csvRecord.getComment());
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals(comment, csvRecord.getComment());
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals(comment, csvRecord.getComment());
    }

    @Test
    public void testGetComment_specialCharacters() throws Exception {
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "!@#$%^&*()_+";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals(comment, csvRecord.getComment());
    }

    @Test
    public void testGetComment_longComment() throws Exception {
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a very long comment that exceeds normal lengths";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        
        Assertions.assertEquals(comment, csvRecord.getComment());
    }
}