package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_9_2Test {

    @Test
    public void testGetComment_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        String comment = "This is a comment";
        long recordNumber = 1L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "";
        long recordNumber = 1L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1L;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertNull(record.getComment());
    }

    @Test
    public void testGetComment_boundaryValues() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        long recordNumber = 1L;

        // Testing single character comment
        String comment = "A";
        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());

        // Testing empty string comment
        comment = "";
        record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());

        // Testing null comment
        comment = null;
        record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertNull(record.getComment());

        // Testing long comment
        comment = "This is a significantly longer comment that should be handled correctly.";
        record = new CSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());
    }
}